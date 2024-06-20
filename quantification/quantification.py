import logging
import os
from typing import Annotated, Optional

import vtk

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
    # Label,
    parameterPack,
)

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLMarkupsROINode, vtkMRMLLabelMapVolumeNode
from slicer import vtkMRMLSequenceNode, vtkMRMLSegmentationNode, vtkMRMLTableNode
from slicer import qMRMLSegmentEditorWidget, qMRMLSegmentSelectorWidget, vtkMRMLSequenceBrowserNode
# from slicer import vtkMRMLPlotSeriesNode, vtkMRMLPlotChartNode

import numpy as np
from scipy import signal
import pydicom as pydcm

import time

#
# quantification
#


class quantification(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Parametric DCE-MRI")
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Development")] # Quantification")]
        self.parent.dependencies = ["SequenceRegistration"]  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Jose L. Ulloa (ISANDEX LTD.), Muhammad Qadir (Austin Health)"] 
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
Slicer Extension to derive non-PK parametric maps from signal intensity analysis of DCE-MRI datasets. 
For up-to-date user guide, go to <a href="https://gthub.com/jlulloaa/..."> official GitHub repository </a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jose L. Ulloa and Muhammad Qadir.
It is derived from the extension <a href="https://github.com/rnadkarni2/SlicerBreast_DCEMRI_FTV"> Slicer DCEMRI FTV </a>. 
This work was (partially) funded by… (grant Name and Number).
""")

        # Additional initialization step after application startup is complete
        # slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


# def registerSampleData():
#     """Add data sets to Sample Data module."""
#     # It is always recommended to provide sample data for users to make it easy to try the module,
#     # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

#     import SampleData

#     iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

#     # To ensure that the source code repository remains small (can be downloaded and installed quickly)
#     # it is recommended to store data sets that are larger than a few MB in a Github release.

#     # quantification1
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="quantification",
#         sampleName="quantification1",
#         # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
#         # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
#         thumbnailFileName=os.path.join(iconsPath, "quantification1.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         fileNames="quantification1.nrrd",
#         # Checksum to ensure file integrity. Can be computed by this command:
#         #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
#         checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
#         # This node name will be used when the data set is loaded
#         nodeNames="quantification1",
#     )

#     # quantification2
#     SampleData.SampleDataLogic.registerCustomSampleDataSource(
#         # Category and sample name displayed in Sample Data module
#         category="quantification",
#         sampleName="quantification2",
#         thumbnailFileName=os.path.join(iconsPath, "quantification2.png"),
#         # Download URL and target file name
#         uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         fileNames="quantification2.nrrd",
#         checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
#         # This node name will be used when the data set is loaded
#         nodeNames="quantification2",
#     )


@parameterPack
class relevantDCEindices:
    
  preContrast: Annotated[float, WithinRange(0.0, 10.0)] = 0.0
  earlyPostContrast: Annotated[float, WithinRange(0.0, 10.0)] = 0.0
  latePostContrast: Annotated[float, WithinRange(0.0, 10.0)] = 0.0

  
  def setDefault(self, maxIndex=0):

      self.preContrast = 0
      self.earlyPostContrast = 1
      self.latePostContrast = maxIndex-1
      

@parameterPack
class timeLabelDCEindices:
    
    preContrastTimeLabel: str=""
    earlyPostContrastTimeLabel: str=""
    latePostContrastTimeLabel: str=""


@parameterPack
class volumeSubtractionIndices:
    
  minuend: Annotated[int, WithinRange(0, 10)] = 1
  subtrahend: Annotated[int, WithinRange(0, 10)] = 0


#
# quantificationParameterNode
#
    

@parameterNodeWrapper
class quantificationParameterNode:
    """
    The parameters needed by module.

    input4DVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    (JU TODO:remove) invertThreshold - If true, will invert the threshold.
    (JU TODO:remove) thresholdedVolume - The output volume that will contain the thresholded volume.
    (JU TODO:remove) invertedVolume - The output volume that will contain the inverted thresholded volume.
    """

    input4DVolume: vtkMRMLSequenceNode
    inputMaskVolume: vtkMRMLSegmentationNode
    outputSequenceMaps: vtkMRMLSequenceNode
    outputLabelMap: vtkMRMLLabelMapVolumeNode

    # # JU - Widgets not yet supported by the Parameters Node Wrapper Infrastructure
    # # Check this for any update: https://github.com/Slicer/Slicer/issues/7308
    # segmentSelectorWidgetParam: qMRMLSegmentSelectorWidget
    # segmentEditorWidgetParam: qMRMLSegmentEditorWidget
    # tableTICNode: vtkMRMLTableNode
    # plotTICNode: vtkMRMLPlotSeriesNode
    # plotChartTICNode: vtkMRMLPlotChartNode

    # Using ParameterPack
    # JU - Controllers for the analysis and display
    indicesDCE: relevantDCEindices
    timingsDCE: timeLabelDCEindices
    
    peakEnhancementThreshold: Annotated[float, WithinRange(0.0, 250.0)] = 70.0
    backgroundThreshold: Annotated[float, WithinRange(0.0, 100.0)] = 60.0
    signalEnhancementRatioThreshold: Annotated[float, WithinRange(0.0, 2.25)] = 1.4
    
    # JU - controllers to display volume subtraction
    subtractIndices: volumeSubtractionIndices
    
    # # JU - Simple Checkboxes to control layers visibility:
    markupROIVisibilityToggle:  bool = True
    segmentMaskVisibilityToggle:  bool = True
    

#
# quantificationWidget
#


class quantificationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """


    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        logging.debug('JU - Initialising parameters node, initial layout and other constants')
        self._parameterNode = None
        self._parameterNodeGuiTag = None
        
        # Setting up the display
        # Customise the layout before starting (https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#customize-view-layout)
        # To get more help, check the code: https://github.com/Slicer/Slicer/blob/main/Libs/MRML/Logic/vtkMRMLLayoutLogic.cxx
        customLayout = """
        <layout type="vertical" split="true" >
        <item splitSize="500">
            <layout type="vertical">
            <item>
                <layout type="horizontal">
                    <item>
                        <view class="vtkMRMLSliceNode" singletontag="Red">
                        <property name="orientation" action="default">Axial</property>
                        <property name="viewlabel" action="default">R</property>
                        <property name="viewcolor" action="default">#F34A33</property>
                        </view>
                    </item>
                    <item>
                        <view class="vtkMRMLSliceNode" singletontag="Yellow">
                        <property name="orientation" action="default">Sagittal</property>
                        <property name="viewlabel" action="default">Y</property>
                        <property name="viewcolor" action="default">#EDD54C</property>
                        </view>
                    </item>
                </layout>
            </item>
            </layout>
        </item>
        <item splitSize="300">
            <layout type="vertical">
            <item>
                <layout type="horizontal">
                    <item>
                        <view class="vtkMRMLPlotViewNode" singletontag="PlotView1">
                        <property name="viewlabel" action="default">P</property>
                        </view>
                    </item>
                    <item>
                        <view class="vtkMRMLTableViewNode" singletontag="TableView1">
                        <property name="viewlabel" action="default">T</property>
                        </view>
                    </item>
                </layout>
            </item>
            </layout>
        </item>
        </layout>
        """

        # Built-in layout IDs are all below 100, so we can choose any large random number
        # for your custom layout ID.
        self.customLayoutId=990
        # The ID for the 3D-render-view-only is 4:
        self.volumeRenderOnlyLayout = 4
        
        # JU - Setting up a layout manager object
        self.layoutManager = slicer.app.layoutManager()
        # Add the custom layout:
        self.layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.customLayoutId, customLayout)
        # JU - Switch to a layout that contains a plot view to create a plot widget.
        # 38 is the layout called "Four-up Quantitative" in the layout dropdown list 
        # (to check which number is currently set, use: slicer.app.layoutManager().layout in slicer's console)
        # self.layoutManager.setLayout(38)
        # Switch to the new custom layout
        self.layoutManager.setLayout(self.customLayoutId)

        # Ensure the markers are visible in all the views:
        viewNodes = slicer.util.getNodesByClass("vtkMRMLAbstractViewNode")
        for viewNode in viewNodes:
            viewNode.SetOrientationMarkerType(slicer.vtkMRMLAbstractViewNode.OrientationMarkerTypeAxes)
        # Display the slice intersections:
        sliceDisplayNodes = slicer.util.getNodesByClass("vtkMRMLSliceDisplayNode")
        for sliceDisplayNode in sliceDisplayNodes:
            sliceDisplayNode.SetIntersectingSlicesVisibility(1)

        # JU - End setting up the layout and display
        
        # JU - To ensure the columns name are consisten between TICTable and TICplot, I define them here:
        self.TICTableRowNames = ["Timepoint [min]", "PE (%)", "Linear Fit"]
        self.SummaryTableRowNames = ["Parameter", "Value", "Units"]
        self.SERTableRowNames = ["SER Range", "Volume (cm3)", "Distribution (%)"]
        # JU - Auxiliar nodes and variables
        self.currentVolume = None
        self.subtractVolume = None
        self.roiNode = None
        self.segmentID = None
        self.colourTableNode = None
        self.timeFrames = None


    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/quantification.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
                
        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = quantificationLogic()
        
        # # JU - Create segment editor to get access to effects
        # # JU - To show segment editor widget (useful for debugging): segmentEditorWidget.show()
        self.segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(self.segmentEditorNode)
        self.ui.segmentEditorWidget.enabled = False
        self.ui.segmentEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
             
        # JU - Output table selector - 
        # TODO: Create a sequence containing each table, that way we could add more tables on the fly
        self.outputTableSelector = slicer.qMRMLNodeComboBox()
        self.outputTableSelector.noneDisplay = _("Create new table")
        self.outputTableSelector.setMRMLScene(slicer.mrmlScene)
        self.outputTableSelector.nodeTypes = ["vtkMRMLTableNode"]
        self.outputTableSelector.enabled = False
        self.outputTableSelector.addEnabled = False
        self.outputTableSelector.selectNodeUponCreation = True
        self.outputTableSelector.renameEnabled = False
        self.outputTableSelector.removeEnabled = False
        self.outputTableSelector.noneEnabled = False
        self.outputTableSelector.setToolTip(_("Select a Table"))
        self.outputTableSelector.setCurrentNode(None)
        # use insertRow to append the new element into a specific row (e.g. FormLayout.insertRow(position, Text, Table))
        # or a more general way by using addWidget:
        self.ui.outputGridLayout.addWidget(self.outputTableSelector, 4, 1, 1)
        
        # JU - Initialise colourmap for SER values. 
        # Has to move it away from the init section to after creating the quantificationLogic object, 
        # so can define a function to allow synchronise quickly any change in the intervals and/or colour codes
        # TODO: May be later on we can add it as part of the configurable parameters in the GUI
        self.ser_segment_labels = self.logic.getSERColourMapDict()

        # Connections - Here there are the connections that aren't made automatically by the Parameter node wrapper
        # JU - Because segmentEditor and Selector widgets are not yet supported by the parameters node wrapper, 
        #     their connections to the scene have be done manually:
        self.ui.segmentEditorWidget.segmentationNodeChanged.connect(self.onSegmentChangeSegmentEditorNode)
        self.ui.inputMaskSelector.currentNodeChanged.connect(self.onNodeChangeInputMaskSelectorNode)
        # JU - This connection manages the visibility of the segment mask
        self.ui.segmentSelectorWidget.currentSegmentChanged.connect(self.updateSelectedSegmentMask)

        # JU - This connection manages the visibility of the table
        self.outputTableSelector.currentNodeChanged.connect(self.onSelectDisplayTable)
        
        # JU - Radio buttons are not avilable yet in the parameter node infraestructure
        self.ui.defaultLayoutViewRadioButton.connect("clicked()", self.checkDefaultVieweLayout)
        self.ui.renderingLayoutViewRadioButton.connect("clicked()", self.checkDefaultVieweLayout)
        
        # JU - Because I want to display/set the current view to whatever slider is moved, I thinks a connector is required:
        self.ui.indexSliderPreContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)
        self.ui.indexSliderEarlyPostContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)
        self.ui.indexSliderLatePostContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons have to be connected manually, because they are controlled manually by the user:
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)
        self.ui.sequenceRegistrationButton.connect("clicked(bool)", self.goToSequenceRegistration)
        self.ui.displaySubtractionButton.connect("clicked(bool)", self.onDisplaySubtractionVolumes)
        self.ui.resetSegmentListButton.connect("clicked(bool)", self.onResetSegmentList)
        
        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()


    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        
        self.removeObservers()


    def enter(self) -> None:
        """Called each time the user opens this module."""
        
        # Make sure parameter node exists and observed
        self.initializeParameterNode()


    def exit(self) -> None:
        """Called each time the user opens a different module."""
        
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)


    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)


    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()


    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.
        logging.debug(f'(initializeParameterNode) Initialise ParameterNode. It runs after setup and everytime the module is (re-)loaded')
        logging.debug(f'(initializeParameterNode) First thing is to Set the ParameterNode (setParameterNode)...')
        self.setParameterNode(self.logic.getParameterNode())
        logging.debug(f'(initializeParameterNode) After Setting up parameter Node, move to initialise')
        logging.debug(f'(initializeParameterNode) If nothing done in the setup, it means the parameterNode is not yet defined.')

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.input4DVolume:
            logging.debug(f'(initializeParameterNode) There is no Input4DVolume - Creating one...')
            firstInputSequenceNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSequenceNode")

            if firstInputSequenceNode:
                self._parameterNode.input4DVolume = firstInputSequenceNode

        # JU 12/06/2024 - The following should happen only if input4D volume exist
        # Initialise the output sequence that'll store the output maps, but only if the input sequence has been defined:

        if self._parameterNode.input4DVolume:
            logging.debug(f'(initializeParameterNode) Input4DVolume is not null - setting up default position')
            self._parameterNode.indicesDCE.setDefault(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
            self.setupBoxROI()

            if not self._parameterNode.outputSequenceMaps:
                logging.debug(f'(initializeParameterNode) outputSequenceMaps does not exist, creating one...')
                self._parameterNode.outputSequenceMaps = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode", "OutputSequenceNode")
                # Set the index to be maps names:
                self._parameterNode.outputSequenceMaps.SetIndexName("Maps")
                self._parameterNode.outputSequenceMaps.SetIndexType(1)  # 0: Numeric; 1: Text
                self._parameterNode.outputSequenceMaps.SetIndexUnit("")
                self.outputSeqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", "OutputSequenceBrowserNode")
                self.outputSeqBrowser.SetAndObserveMasterSequenceNodeID(self._parameterNode.outputSequenceMaps.GetID())

            # # Select default input nodes if nothing is selected yet to save a few clicks for the user
            if not self._parameterNode.inputMaskVolume:
                firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
                
                if firstVolumeNode:
                    self._parameterNode.inputMaskVolume = firstVolumeNode
                
                elif self._parameterNode.input4DVolume:
                    self._parameterNode.inputMaskVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation Mask")

            # Now that the segmentation mask has been created, add a default segmentation to initialise it:
            if self._parameterNode.inputMaskVolume:
                # Get the number of segmentations attached to the segmentation node:
                segmentations = self._parameterNode.inputMaskVolume.GetSegmentation()
                
                if segmentations.GetNumberOfSegments() < 1:
                    # Create a new segmentation and attach it to the inputMaskVolume node:
                    segmentations.AddEmptySegment()
                    
                self.ui.segmentEditorWidget.setSegmentationNode(self._parameterNode.inputMaskVolume)
                self.ui.segmentEditorWidget.setSourceVolumeNode(self.currentVolume) # self.currentVolume)
                
                self.segmentID = self.ui.segmentSelectorWidget.currentSegmentID()
                
            # # Define a default output Label Map:
            if not self._parameterNode.outputLabelMap:
                firstOutputLabelMap = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLLabelMapVolumeNode")

                if firstOutputLabelMap:
                    self._parameterNode.outputLabelMap = firstOutputLabelMap

                else:
                    # There are no output label map available, so create one by default:
                    self._parameterNode.outputLabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "SER Label Map")

            # Create a default display node, so I can associate the colour table:
            self._parameterNode.outputLabelMap.CreateDefaultDisplayNodes()

            ser_labels_colour_table = slicer.mrmlScene.GetNodesByName("SER_labels")
            if (self.colourTableNode is None):

                # colourTableNode does not exist, let see whether the SER_labels colour table already exist
                if ser_labels_colour_table.GetNumberOfItems() > 0:
                    # Then assign the existing table:
                    self.colourTableNode = ser_labels_colour_table.GetItemAsObject(0)

                else:
                    logging.debug(f'Creates new colour table node...')
                    self.colourTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "SER_labels")

            self.colourTableNode.SetTypeToUser()

            # make the color table selectable in the GUI outside Colors module
            self.colourTableNode.HideFromEditorsOff()
            self.setupColourTable()

            # # Associate the colour table with the label map --> Pay attention to the use cases, because there is an error at some point (not yet clear when though)
            self._parameterNode.outputLabelMap.GetDisplayNode().SetAndObserveColorNodeID(self.colourTableNode.GetID())            

            # Select default plot and tables nodes, to avoid creating new ones:
            if not self.outputTableSelector.currentNode():
                self.TICTableNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLTableNode")
                self.SummaryTableNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLTableNode")
                self.SERDistributionTableNode = slicer.mrmlScene.GetNthNodeByClass(2, "vtkMRMLTableNode")

                if not self.TICTableNode:
                    self.TICTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "TIC Table")

                # TODO: Check how to assign multiple tables to selector
                if not self.SummaryTableNode:
                    self.SummaryTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "Summary Table")

                if not self.SERDistributionTableNode:
                    self.SERDistributionTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "SER Table")

                self.outputTableSelector.setCurrentNode(self.SERDistributionTableNode)

            numberOfPlotSeriesNode = slicer.mrmlScene.GetNodesByClass("vtkMRMLPlotSeriesNode").GetNumberOfItems()

            if numberOfPlotSeriesNode == 0:
                firstPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "TIC plot")
                secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Linear Fit")

            elif numberOfPlotSeriesNode == 1:
                firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
                secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Linear Fit")

            else:
                firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
                secondPlotSeriesNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLPlotSeriesNode")
                
            self.plotSeriesNode = firstPlotSeriesNode
            self.plotCurveFitNode = secondPlotSeriesNode
            self.plotSeriesNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())
            self.plotCurveFitNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())

            firstPlotChartNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotChartNode")

            if not firstPlotChartNode:
                firstPlotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", "TIC chart")

            self.plotChartNode = firstPlotChartNode
            # Ensure there is no previous charts in the node (to avoid multiple legends appearing when re-loading):
            self.plotChartNode.RemoveAllPlotSeriesNodeIDs()
                    
            # self.plotChartNode.SetAndObservePlotSeriesNodeID(self.plotSeriesNode.GetID())
            # self.plotChartNode.SetAndObservePlotSeriesNodeID(self.plotCurveFitNode.GetID())
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotSeriesNode.GetID())
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotCurveFitNode.GetID())
            
            # Finally, (re-)configure the plot window
            self.configurePlotSeriesNode()

        logging.debug(f'(initializeParameterNode) End of initialisation')
     
     
    def setParameterNode(self, inputParameterNode: Optional[quantificationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        logging.debug(f'(setParameterNode) Running setParameterNode. ')
        logging.debug(f'(setParameterNode) If self._parameterNode is None, it will set it up from the quantificationParameterNode class')

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            logging.debug(f'(setParameterNode) self._parameterNode is not null. Disconnecting the GUI and removing the Observer...')

            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            logging.debug(f'(setParameterNode) Observer removed')

        logging.debug('(setParameterNode) Setting the parameter Node to input Parameter node. It will force the parameterNode to be defined')
        self._parameterNode = inputParameterNode

        if self._parameterNode:
            logging.debug('(setParameterNode) Parameter Node is not null. Assigning a Node GUI Tag')
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            
            if self._parameterNode.input4DVolume:
                logging.debug(f'(setParameterNode) input4Dvolume is not null, so we are setting up eveyrthing else...')
                # Setup default positions for the sliders: preContrast = 0; earlyPostContrast = 1; latePostContrast = N_Nodes
                self.setMaxIndexSelector(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
                self.setCurrentVolumeFromIndex(indexAsDouble=self._parameterNode.indicesDCE.earlyPostContrast)
                # self.setupBoxROI()
                # self.addObserver(self._parameterNode.input4DVolume, vtk.vtkCommand.ModifiedEvent, self._clickToDisplay)
                # print(f'Setting up sequence dependencies...')
                # self.onInputSelect()
                # print(f'(End Step 3a)')
                # self.inputSeqBrowser = slicer.modules.sequences.logic().GetFirstBrowserNodeForSequenceNode(self._parameterNode.input4DVolume)
                # self.inputSeqBrowser = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSequenceBrowserNode")
                # self.inputSeqBrowser.SetAndObserveMasterSequenceNodeID(self._parameterNode.input4DVolume.GetID())
                # self.configureView()
                # if self.timings is None:
                # self.timings = self.getAcquisitionTimings()
                # self.setTimeValueOnSlider()
                # print(f'Call within setParameterNode: Setup Index Selector and Widget status')
                # # JU - Based on the sequence loaded, define the maximum index on the sliders
                # self.setMaxIndexSelector(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
                # # JU - setup the initial view of the early post-contrast volume
                # self.setCurrentVolumeFromIndex(self._parameterNode.earlyPostContrastIndex)
                # # JU - Add the Reference BOX ROI to crop the analysis:
                # self.roiNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsROINode")
                # if self.roiNode is None:
                #     # Create a new ROI that will be fit to volumeNode
                #     self.roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "RefBox")
                
                # # JU - If not done before, enable the segment editor
                # self.ui.segmentEditorWidget.enabled = True
                logging.debug(f'(setParameterNode) self.input4DVolume is not null, so we are calling the function _checkCanApply')
                self._checkCanApply()
                
        logging.debug(f'(setParameterNode) All setup with the Parameter node. If parameterNode is empty, nothing was done here.')


    def _checkCanApply(self, caller=None, event=None) -> None:
        logging.debug(f'(_checkCanApply) Check whether all required parameters are setup to enable the processing...')

        if self._parameterNode and self._parameterNode.input4DVolume:
            logging.debug(f'(_checkCanApply) everything seems ready to run the analysis, applying final setups...')
            ## if self._parameterNode.input4DVolume:
            logging.debug(f'(_checkCanApply) Volume Size: {self._parameterNode.input4DVolume.GetNumberOfDataNodes()}')
            logging.debug(f'(_checkCanApply) Setting the maximum values for the index sliders - If the selector was changed, it will make sense, otherwise, it is redundant')
            self.setMaxIndexSelector(self._parameterNode.input4DVolume.GetNumberOfDataNodes()) #self._parameterNode.indicesDCE

            logging.debug(f'(_checkCanApply) Setting the display to a valid volume from the selected sequence - If the selector was changed, it makes sense, otherwise it will not')
            self.setCurrentVolumeFromIndex()
            # self.onInputSelect()

            logging.debug(f'(_checkCanApply) Ensure the index sliders and subtraction buttons are enabled...')
            self.ui.relevantIndicesCollapsibleButton.enabled = True
            self.ui.relevantIndicesCollapsibleButton.collapsed = False
            self.ui.displaySubtractionCollapsibleButton.enabled = True
            self.ui.displaySubtractionCollapsibleButton.collapsed = False
            self.ui.displaySubtractionButton.enabled=True
            self.ui.sequenceRegistrationButton.enabled = True
            # Check the visibility of the ROI
            self.toggleROIsView() # ===> Add an update to the ROI so it can reset when loading new data
            # self.checkVolumeRenderingVieweLayout()
            # But, we need to check the maximum number of frames
            # self.onInputSelect()
            # ## if self.timings is None:

            logging.debug(f'(_checkCanApply) update the acquisition times from the data. As the previous lines, it the selector was changed, it will make sense, otherwise, it not needed...')
            self.timings = self.getAcquisitionTimings()

            logging.debug(f'(_checkCanApply) Update the timing beside each slider.')
            self.setTimeValueOnSlider()

            if self._parameterNode.inputMaskVolume:
                logging.debug(f'(_checkCanApply) Last check to enable Apply button')
                self.ui.parametersCollapsibleButton.enabled=True
                self.ui.parametersCollapsibleButton.collapsed=False
                self.ui.peakEnhancementThreshold.enabled = True
                self.ui.signalEnhancementRatioThreshold.enabled = True
                self.ui.backgroundThreshold.enabled = True
                self.ui.segmentEditorCollapsibleButton.collapsed=False
                self.ui.segmentEditorWidget.enabled = True
                self.ui.outputsCollapsibleButton.enabled = True
                self.ui.outputsCollapsibleButton.collapsed = False
                self.outputTableSelector.enabled = True
                self.ui.applyButton.toolTip = _("Compute FTV parameters")
                self.ui.applyButton.enabled = True
                self.ui.resetSegmentListButton.enabled = True
                logging.debug(f'(_checkCanApply) end testing inside input4DVolume')

        else:
            logging.debug(f'(_checkCanApply) parameterNode and input4DVolume are not enabled yet, so nothing done...')
            self.ui.relevantIndicesCollapsibleButton.enabled = False
            self.ui.relevantIndicesCollapsibleButton.collapsed = False
            self.ui.displaySubtractionCollapsibleButton.enabled = False
            self.ui.displaySubtractionCollapsibleButton.collapsed = True
            self.ui.displaySubtractionButton.enabled=False
            self.ui.segmentEditorCollapsibleButton.collapsed=True
            self.ui.parametersCollapsibleButton.enabled=False
            self.ui.parametersCollapsibleButton.collapsed=True
            self.ui.applyButton.toolTip = _("Select input sequence volume")
            self.ui.applyButton.enabled = False

        logging.debug(f'(_checkCanApply) End of function')
       
            
    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            # self.update_plot_window()
            # Update timings including bolus time (if available from the DICOM metadata)
            self.timings = self.getAcquisitionTimings(getBolus=True)
            # Compute output
            self.logic.process(self._parameterNode.input4DVolume, 
                               self._parameterNode.inputMaskVolume, 
                               self._parameterNode.outputSequenceMaps, 
                               self._parameterNode.outputLabelMap,
                               self.roiNode,
                               {'TICTable': [self.TICTableNode, self.TICTableRowNames],
                                'SummaryTable': [self.SummaryTableNode, self.SummaryTableRowNames],
                                'SERSummaryTable': [self.SERDistributionTableNode, self.SERTableRowNames]},
                               int(self._parameterNode.indicesDCE.preContrast),
                               int(self._parameterNode.indicesDCE.earlyPostContrast),
                               int(self._parameterNode.indicesDCE.latePostContrast),
                               self.timings,
                               self._parameterNode.peakEnhancementThreshold,
                               self._parameterNode.signalEnhancementRatioThreshold,
                               self._parameterNode.backgroundThreshold,
                               self.segmentID)
            self.update_plot_window()
            
            try:
                # Set the X-range of the graph to be the even number closest to 125% of the maximum
                xRange = np.array(self.TICTableNode.GetTable().GetColumn(0).GetFiniteRange())
                xMax = np.floor(xRange[1] * 1.25)
                xLims = [xRange[0],  xMax + ( xMax % 2 )]
                self.plotChartNode.XAxisRangeAutoOff()
                self.plotChartNode.SetXAxisRange(xLims)
                
            except:
                logging.error('Cannot set the limits in the X-axis')


    # JU - user-defined connnector functions
    def goToSequenceRegistration(self) -> None:
        
        # Warn that it will move away from the module
        warnText = "This will take you to another module.\nTo come back, go to Modules -> Quantification -> Parameteric DCE-MRI"
        ok = slicer.util.confirmOkCancelDisplay(warnText, windowTitle="WARNING")
        
        if ok:
            slicer.util.selectModule("SequenceRegistration")


    def checkDefaultVieweLayout(self) -> None:
        
        if self.ui.defaultLayoutViewRadioButton.checked:
            self.layoutManager.setLayout(self.customLayoutId)
        else:
            self.layoutManager.setLayout(self.volumeRenderOnlyLayout)
            
                        
    def checkVolumeRenderingVieweLayout(self) -> None:

        if self._parameterNode.renderingLayoutViewToggle:
            self.layoutManager.setLayout(self.volumeRenderOnlyLayout)
        else:
            self.layoutManager.setLayout(self.customLayoutId)

        self._parameterNode.defaultLayoutViewToggle = not self._parameterNode.renderingLayoutViewToggle
       
            
    def toggleROIsView(self) -> None:
        
        if self.roiNode:
            self.roiNode.SetDisplayVisibility(self._parameterNode.markupROIVisibilityToggle)

        if self.segmentID:
            maskDisplayNode = self._parameterNode.inputMaskVolume.GetDisplayNode()
            maskDisplayNode.SetSegmentVisibility(self.segmentID, self._parameterNode.segmentMaskVisibilityToggle) 
        
    
    def onSegmentChangeSegmentEditorNode(self) -> None:
        
        self.ui.inputMaskSelector.setCurrentNode(self.ui.segmentEditorWidget.segmentationNode())
        
    
    def onNodeChangeInputMaskSelectorNode(self) -> None:
        
        self.ui.segmentEditorWidget.setSegmentationNode(self.ui.inputMaskSelector.currentNode())
    
    
    def onSequenceChangeInputSelectorNode(self) -> None:

        if self._parameterNode is not None:
            self._parameterNode.input4DVolume = self.ui.inputSelector.currentNode()
            logging.debug('(onSequenceChangeInputSelectorNode) Changed the main input selector node...')
            self.onInputSelect()
            logging.debug(f'(onSequenceChangeInputSelectorNode) updating aquisition times...')
            self.timings = self.getAcquisitionTimings()
            logging.debug(f'(onSequenceChangeInputSelectorNode) done updating aquisition times...')

        
    def onInputSelect(self):
        
        logging.debug(f'Step 3a: ONINPUTSELECT, First Branch if INPUT4DVolume, run after (re-)loadind')

        if not self._parameterNode.input4DVolume: #self.ui.inputSelector.currentNode():
            # print('No nodes to use')
            numberOfDataNodes = 0
            
        else:
            numberOfDataNodes = self._parameterNode.input4DVolume.GetNumberOfDataNodes() #self.ui.inputSelector.currentNode().GetNumberOfDataNodes()

        logging.debug(f'Number of items in the sequence: {numberOfDataNodes}')
        self.setMaxIndexSelector(numberOfDataNodes)
        logging.debug(f'(End Step 3.1a)')
    
    
    def updateSelectedSegmentMask(self) -> None:

        self.segmentID = self.ui.segmentSelectorWidget.currentSegmentID()

        # # Set visibility for the selected segmentation label:

        if self._parameterNode:
            # self.segmentID = self.ui.segmentSelectorWidget.currentSegmentID()
            displayNode = self._parameterNode.inputMaskVolume.GetDisplayNode()
            displayNode.SetAllSegmentsVisibility(False) # Hide all segments
            displayNode.SetSegmentVisibility(self.segmentID, True)
        # JU - TODO: set viewer to the slice where the roi can be seen (decide if using the first, middle, last or any other relevant for the study)

    
    # From MultiVolumeImporterPlugin 
    # (https://github.com/fedorov/MultiVolumeImporter/blob/c8a37eb5e4f35b78ccc9287b298457a064c9d001/MultiVolumeImporterPlugin.py#L779)
    def tm2ms(self,tm) -> None:
        
        if len(tm)<6:
            return 0

        try:
            hhmmss = tm.split('.')[0]
        except:
            hhmmss = tm

        try:
            ssfrac = float('0.'+tm.split('.')[1])
        except:
            ssfrac = 0.

        if len(hhmmss)==6: # HHMMSS
            sec = float(hhmmss[0:2])*60.*60.+float(hhmmss[2:4])*60.+float(hhmmss[4:6])
        elif len(hhmmss)==4: # HHMM
            sec = float(hhmmss[0:2])*60.*60.+float(hhmmss[2:4])*60.
        elif len(hhmmss)==2: # HH
            sec = float(hhmmss[0:2])*60.*60.
        else:
            raise OSError("Invalid DICOM time string: "+tm+" (failed to parse HHMMSS)")

        sec = sec+ssfrac

        return sec*1000.
        
    
    def getAcquisitionTimings(self, getBolus=False):
        
        if self._parameterNode.input4DVolume is not None:
            
            if self._parameterNode.input4DVolume.GetAttribute("MultiVolume.FrameLabels") is not None:
                # Get acquisition times from DICOM metadata (output in ms)
                self.timeFrames = np.array(self._parameterNode.input4DVolume.GetAttribute("MultiVolume.FrameLabels").split(',')).astype(float)
            else:
                nt = self._parameterNode.input4DVolume.GetNumberOfDataNodes()
                # normalise the time axis to nt = 1min = 60x10e3 [ms] to be consistent with the calculations  
                self.timeFrames = np.linspace(0, nt*60.0*1.0e3, num=nt, endpoint=True)

            logging.debug(f'(getAcquisitionTimings) Frame Labels: {self.timeFrames}')
            
            if getBolus:
                
                # Identify Bolus injection time:
                get_bolus_time_start = time.perf_counter()
                
                # Get the bolus time relative to the start of the acquisition time
                # Unfortunately, still have to read all the files to derive it
                fileList = []
                acquisitionTimes = []
                bolusInjTimes = []
                
                # Contrast Bolus Start Time is recorded in different Dicom attributes, 
                # depending on the manufacturer and sequence, so far, the following are known:
                # Philips - Dyn eThrive: (0018, 1042) ContrastBolusStartTime
                contrastBolusAttribute = ['ContrastBolusStartTime']

                if self._parameterNode.input4DVolume.GetAttribute("MultiVolume.FrameFileList") is not None:
                    fileList = self._parameterNode.input4DVolume.GetAttribute("MultiVolume.FrameFileList").split(',')

                for ifile in fileList:
                    dcmMetaData = pydcm.dcmread(ifile, stop_before_pixels=True)
                    acquisitionTimes.append((dcmMetaData.AcquisitionTime))
                    for cb_attr in contrastBolusAttribute:
                        if cb_attr in dcmMetaData:
                            bolusInjTimes.append((dcmMetaData.ContrastBolusStartTime))
                            break
                        
                if acquisitionTimes:
                    acquisitionTimeStart = sorted(acquisitionTimes)[0]
                else:
                    acquisitionTimeStart = '0'

                if bolusInjTimes:
                    bolusInjTimeList = sorted(bolusInjTimes)[0]
                    bolusInjTimeRelativeToStart = self.tm2ms(bolusInjTimeList) - self.tm2ms(acquisitionTimeStart)
                else:
                    bolusInjTimeList = '0'
                    bolusInjTimeRelativeToStart = 0.0


            else:
                bolusInjTimeRelativeToStart = 0.0
                
            timings = {'timepoints': self.timeFrames, 
                       'injectionTime': bolusInjTimeRelativeToStart}
            
        else:
            timings = None

        get_bolus_time_end = time.perf_counter()
        if getBolus :
            print(f'(getAcquisitionTimings) Elapsed time to get bolus time: {get_bolus_time_end - get_bolus_time_start}')
            
        return timings


    def setTimeValueOnSlider(self) -> None:

        logging.debug(f'(setTimeValueOnSider) Step 3b: SETTIMAVALUEONSLIDER, First Branch if INPUT4DVolume, run after (re-)loadind')
        if self.timeFrames is not None:
            self.ui.labelTimePreContrast.text = f'{self.timeFrames[int(self._parameterNode.indicesDCE.preContrast)]/(1000*60):.1f}[min]'
            self.ui.labelTimeEarlyPostContrast.text = f'{self.timeFrames[int(self._parameterNode.indicesDCE.earlyPostContrast)]/(1000*60):.1f}[min]'
            self.ui.labelTimeLatePostContrast.text = f'{self.timeFrames[int(self._parameterNode.indicesDCE.latePostContrast)]/(1000*60):.1f}[min]'

        
    def setupBoxROI(self) -> None:

        self.roiNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsROINode")

        if self._parameterNode is not None:

            if (self.roiNode is None) & (self.currentVolume is not None):
                # setup the ROI
                self.roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "RefBox")
                # JU - Setup a Box ROI to crop the volume of interest. When running this function, the input volume must have been defined:
                # Fit the ROI to the volume on display:
                self.logic.fitBoxROImarkupToVolume(self.currentVolume, self.roiNode)
                # Set the initial dimensions to a fraction of the volume size
                halfSize = tuple([dim/4.0 for dim in self.roiNode.GetSize()])
                self.roiNode.SetSize(halfSize)
                # self.roiNode.SetRadiusXYZ(self.currentVolume.GetOrigin())
                new_roi_bounds = [0]*6
                self.roiNode.GetBounds(new_roi_bounds)
                print(f'bBox Size: {self.roiNode.GetSize()}')
                
                # TODO: enable a checkbox to control BoxROI visibility
                # self.toggleROIsView()
                # self.roiNode.SetDisplayVisibility(self._parameterNode.markupROIVisibilityToggle)

                
    # JU - separate to refresh the index selctors everytime the module is loaded (not only when the input selector changes)
    def setMaxIndexSelector(self, maxIndex) -> None:
        
        logging.debug(f'Step 3.1a: SETMAXINDEXSELECTOR, Sub-Call made by ONINPUTSELECT (Branch if INPUT4DVolume), run after (re-)loadind')
        
        for sequenceItemSelectorWidget in [self.ui.indexSliderPreContrast, self.ui.indexSliderEarlyPostContrast, self.ui.indexSliderLatePostContrast, self.ui.minuendIndexSelector, self.ui.subtrahendIndexSelector]:

            if maxIndex < 1:
                sequenceItemSelectorWidget.maximum = 0
                sequenceItemSelectorWidget.enabled = False
            else:
                sequenceItemSelectorWidget.maximum = maxIndex-1
                sequenceItemSelectorWidget.enabled = True
                    
        
        
    def setCurrentVolumeFromIndex(self, indexAsDouble=None) -> None:

        sequenceBrowserNode = self.logic.findBrowserForSequence(self._parameterNode.input4DVolume)
        # # JU - DEBUGMODE
        logging.debug(f'Selected Sequence from browser is {sequenceBrowserNode.GetName()}')

        if indexAsDouble is not None:
            sequenceBrowserNode.SetSelectedItemNumber(int(indexAsDouble))

        # self.currentVolume = sequenceBrowserNode.GetProxyNode(self._parameterNode.input4DVolume) #self.ui.inputSelector.currentNode())
        # JU TODO: can we replace this by an observers into a scalar node?
        self.currentVolume = sequenceBrowserNode.GetProxyNode(self.ui.inputSelector.currentNode())

        # Update the sequence browser toolbar with the sequeence selected in the input selector
        slicer.modules.sequences.toolBar().setActiveBrowserNode(sequenceBrowserNode)        

        # # JU - This displays the selected volume in the viewer
        # # (https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#show-a-volume-in-slice-views)
        self.logic.updateViewer(self.currentVolume)

    
    def onDisplaySubtractionVolumes(self):#, minuendIndex=None, sustrahendIndex=None) -> None: # requires at least four inputs: sequence Volume, minuend Volume index, sustraend Volume index and display Node:

        minuendIndex = self._parameterNode.subtractIndices.minuend
        logging.debug(f'1.a) Minuend: {minuendIndex}')

        sustrahendIndex = self._parameterNode.subtractIndices.subtrahend
        logging.debug(f'2.a) Subtrahend: {sustrahendIndex}')
            
        
        self.subtractVolume = self.logic.subtractVolumes(self._parameterNode.input4DVolume, minuendIndex, sustrahendIndex, self.subtractVolume)
        self.logic.updateViewer(self.subtractVolume)

    def onResetSegmentList(self):
        self.logic.resetSegmentList(self._parameterNode.inputMaskVolume)
        
        
    def configurePlotSeriesNode(self) -> None:
        
        # print('Configuring Plot Series and Chart Window...')
        # Configure Plot Series:
        self.plotSeriesNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotSeriesNode.SetYColumnName(self.TICTableRowNames[1])
        self.plotSeriesNode.SetPlotType(self.plotSeriesNode.PlotTypeScatter)
        self.plotSeriesNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        self.plotSeriesNode.SetColor(0, 0.6, 1.0)
        
        # Configure Plot Linear Fit
        self.plotCurveFitNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotCurveFitNode.SetYColumnName(self.TICTableRowNames[2])
        self.plotCurveFitNode.SetPlotType(self.plotCurveFitNode.PlotTypeScatter)
        self.plotCurveFitNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        self.plotCurveFitNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleNone)
        self.plotCurveFitNode.SetColor(0, 0, 0)
        
        # Configure Chart node
        self.configurePlotChartNode()

    
    def configurePlotChartNode(self) -> None:
        
        # Configure Plot Chart Window:
        self.plotChartNode.SetTitle("Time Intensity Curves")
        self.plotChartNode.SetXAxisTitle(self.TICTableRowNames[0])
        self.plotChartNode.SetYAxisTitle(self.TICTableRowNames[1])
        self.plotChartNode.LegendVisibilityOn()
        self.plotChartNode.SetLegendFontSize(10)
        self.plotChartNode.SetXAxisRangeAuto(True)
        self.plotChartNode.SetYAxisRangeAuto(True)
        
        # Assign Plot Series to Chart window:
        self.plotWidget = self.layoutManager.plotWidget(0)
        self.plotViewNode = self.plotWidget.mrmlPlotViewNode()
        self.plotViewNode.SetPlotChartNodeID(self.plotChartNode.GetID())
    
    
    def onSelectDisplayTable(self):
        self.logic.displayTable(self.outputTableSelector.currentNode())
    
        
    def update_plot_window(self) -> None:
        
        # table to display by default: 
        self.logic.displayTable(self.SERDistributionTableNode)
        # Ensure the outputTableSelector is back to the table on display:
        self.outputTableSelector.setCurrentNode(self.SERDistributionTableNode)
        
        # JU - update plot name according to the selected segment name:
        print(f'(update_plot_window) SegmentID: {self.segmentID}')
        segmentations = self._parameterNode.inputMaskVolume.GetSegmentation()
        self.plotSeriesNode.SetName(segmentations.GetSegment(self.segmentID).GetName())
        # remove any previous plots from the chart:
        # self.plotChartNode.RemoveAllPlotSeriesNodeIDs()
        print(f'(update_plot_window) updated plot window')

        # (Re-)Configure Plot Chart window:
        self.plotWidget.update()
        # self.configurePlotChartNode()
    
    
    def setupColourTable(self) -> None:

        nLabels = len(self.ser_segment_labels)
        self.colourTableNode.SetNumberOfColors(nLabels)
        self.colourTableNode.SetNamesInitialised(True) # prevent automatic color name generation

        for idx, (legend, [r,g,b,a]) in enumerate(self.ser_segment_labels.items()):
            success = self.colourTableNode.SetColor(idx, legend, r, g, b, a)
            if success:
                logging.debug(f'(setupColourTable) {idx}) Legend: {legend} - (success: {success})')


        

#
# quantificationLogic
#


class quantificationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        
        # Constants:
        self.EPSILON = 1.0e-6
        self.INF_THRESHOLD = 1.0e6
        self.UPPER_ENH_THRESHOLD = 5.0e6
        self.PIXEL_CONNECTIVITY = 4
        self.FG_OPACITY = 0.5
        self.LB_OPACITY = 0.0
        self.SERColourMapDictionary = None
        
        
    def getParameterNode(self):
        return quantificationParameterNode(super().getParameterNode())


    # JU - User-defined functions
    def findBrowserForSequence(self, sequenceNode):
        # JU - debug
        # TODO: Check error when loading data before invoking the module for the first time:
        # [VTK] vtkMRMLSequenceBrowserNode::IsSynchronizedSequenceNode failed: sequenceNode is invalid
        # [Qt] void qMRMLSegmentEditorWidget::setSourceVolumeNode(vtkMRMLNode *)  failed: need to set segment editor and segmentation nodes first

        # print(f'Checking whether this message appears when loading data before invoking the module...')
        browserNodes = slicer.util.getNodesByClass("vtkMRMLSequenceBrowserNode")
        for browserNode in browserNodes:
            if browserNode.IsSynchronizedSequenceNode(sequenceNode, True):
                return browserNode
        return None
    
    
    def getSERColourMapDict(self):
        
        if self.SERColourMapDictionary is None:
            self.setSERColourMapDict()
        
        return self.SERColourMapDictionary
    
        
    def setSERColourMapDict(self):

        """ In the FTV Extension, they split the intervals as follows:
        ]0, 0.9]: Blue (0, 0, 1)
        ]0.9, 1.1]: Purple (0.5, 0, 0.5)
        ]1.1, 1.3]: Green (0, 1, 0)
        ]1.3, 1.75]: Red (1, 0, 0)
        ]1.75, 3.0]: Yellow (1, 1, 0)
        >0.0 & <3.0 (i.e. No SER): White (1, 1, 1)
        """
        alfa = 1
        serMapInterval = [0.00, 0.90, 1.0, 1.30, 1.75, 3.00]
        # serMapInterval = [0.00, 0.90, 1.00, 1.10]
        serMapColours = [[0.0, 0.0, 0.0, 0.0], # black & transparent so it can be overlaid with the MIP
                         [0.0, 0.0, 1.0, alfa], # blue
                         [0.5, 0.0, 0.5, alfa], # purple
                         [0.0, 1.0, 0.0, alfa], # green
                         [1.0, 0.0, 0.0, alfa], # red
                         [1.0, 1.0, 0.0, alfa], # yellow
                         [1.0, 1.0, 1.0, alfa] # white (>MaxSER)
                         ]
        # serMapColours = np.array(serMapColours)[[0,2,3,-1]]
        self.SERLevelLB = serMapInterval[:-1]
        self.SERLevelUB = serMapInterval[1:]
        self.SERColourMapDictionary = {'non SER': serMapColours[0]}
        self.SERlegend = []
        for idx, (lb, ub) in enumerate(zip(self.SERLevelLB, self.SERLevelUB)):
            legend = f'{lb} < SER ≤ {ub}'
            self.SERColourMapDictionary[legend] = serMapColours[idx+1]
            self.SERlegend.append(legend)
        # Add upper limit legent (>MaxSER)
        legend = f'{serMapInterval[-1]} < SER '
        self.SERColourMapDictionary[legend] = serMapColours[-1]
        self.SERlegend.append(legend)
        
        
    def getSegmentList(self, maskVolumeNode):

        nsegments = maskVolumeNode.GetSegmentation().GetNumberOfSegments()
        segmentList = [maskVolumeNode.GetSegmentation().GetNthSegment(idx) for idx in range(nsegments)]

        return segmentList


    def displayTable(self, currentTable):
        slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(currentTable.GetID())
        currentTable.SetUseColumnTitleAsColumnHeader(True)  # Make column titles visible (instead of column names)
        slicer.app.applicationLogic().PropagateTableSelection()
    
            
    def updateViewer(self, backgroundVolume, foregroundVolume=None, labelVolume=None, labelOpacity=None):
        
        if foregroundVolume is not None:
            foregroundOpacity=self.FG_OPACITY
            cornerLabel = foregroundVolume.GetName()
        else:
            foregroundOpacity = None
            cornerLabel = backgroundVolume.GetName()
        
        if labelVolume is not None:
            labelOpacity = self.LB_OPACITY
            colorLegendDisplayNode = slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(labelVolume)
            colorLegendDisplayNode.ScalarVisibilityOn()
            colorLegendDisplayNode.GetLabelTextProperty().SetFontFamilyToArial()
        
        for channels in ["Red", "Yellow"]:
            view = slicer.app.layoutManager().sliceWidget(channels).sliceView()
            view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft, cornerLabel)
                  
        slicer.util.setSliceViewerLayers(background=backgroundVolume, 
                                         foreground=foregroundVolume,
                                         foregroundOpacity=foregroundOpacity,
                                         label=labelVolume, labelOpacity=labelOpacity)
    
        
    def showVolumeRenderingMIP(self, volumeNode, useSliceViewColors=True):
        """
        Source code from: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository/volumes.html#show-volume-rendering-using-maximum-intensity-projection
        To get more help: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#show-volume-rendering-automatically-when-a-volume-is-loaded
        Render volume using maximum intensity projection
        :param useSliceViewColors: use the same colors as in slice views.
        
        How to use it:
        volumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        showVolumeRenderingMIP(volumeNode)        
        
        """
        
        # Get/create volume rendering display node
        volRenLogic = slicer.modules.volumerendering.logic()
        displayNode = volRenLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)
        if not displayNode:
            displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
        # Choose MIP volume rendering preset
        if useSliceViewColors:
            volRenLogic.CopyDisplayToVolumeRenderingDisplayNode(displayNode)
        else:
            scalarRange = volumeNode.GetImageData().GetScalarRange()
            if scalarRange[1]-scalarRange[0] < 1500:
            # Small dynamic range, probably MRI
                displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName("MR-MIP"))
            else:
                # Larger dynamic range, probably CT
                displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName("CT-MIP"))
        # Switch views to MIP mode
        for viewNode in slicer.util.getNodesByClass("vtkMRMLViewNode"):
            viewNode.SetRaycastTechnique(slicer.vtkMRMLViewNode.MaximumIntensityProjection)
        # Show volume rendering
        displayNode.SetVisibility(True)

    # TODO: define function to add bounding box to the 3D rendering, as shown here: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#markups-roi
    # def draw_bounding_box(self, segmentID, markupNode):

    # Delete some segments in the segment editor (by giving the list "items_to_remove" of segments to delete) or 
    # delete all segments in the list and create a new empty one (default behaviour)
    def resetSegmentList(self, segmentationVolumeNode, items_to_remove=None):
        
        maskSegmentations = segmentationVolumeNode.GetSegmentation()
        if items_to_remove is not None:
            for segment_iID in maskSegmentations.GetSegmentIDs():
                segment_i = maskSegmentations.GetSegment(segment_iID)
                if segment_i.GetName() in items_to_remove:
                    maskSegmentations.RemoveSegment(segment_i)
        else:
            # Remove all segments and create a new one empty
            for segment_iID in maskSegmentations.GetSegmentIDs():
                segment_i = maskSegmentations.GetSegment(segment_iID)
                maskSegmentations.RemoveSegment(segment_i)
            maskSegmentations.AddEmptySegment()

    # JU - Crop Volume from ROI Box:
    def cropVolumeFromROI(self, inputVolumeArray, referenceBoxROINode, referenceScalarVolumeNode):
        
        slicer.util.updateVolumeFromArray(referenceScalarVolumeNode, inputVolumeArray)

        cropVolumeLogic = slicer.modules.cropvolume.logic()
        cropVolumeParameterNode = slicer.vtkMRMLCropVolumeParametersNode()
        cropVolumeParameterNode.SetROINodeID(referenceBoxROINode.GetID())
        cropVolumeParameterNode.SetInputVolumeNodeID(referenceScalarVolumeNode.GetID())
        cropVolumeParameterNode.SetVoxelBased(True)
        # cropVolumeLogic.SnapROIToVoxelGrid(cropVolumeParameterNode)  # rotates the ROI to match the volume axis directions
        cropVolumeLogic.Apply(cropVolumeParameterNode)
        croppedVolumeNode = slicer.mrmlScene.GetNodeByID(cropVolumeParameterNode.GetOutputVolumeNodeID())
        croppedVolume = slicer.util.arrayFromVolume(croppedVolumeNode)
        
        slicer.mrmlScene.RemoveNode(croppedVolumeNode)
        
        return croppedVolume
    
    def cropSequenceVolumeFromROI(self, inputSequenceArray, referenceBoxROINode, referenceScalarVolumeNode):
        
        # cropVolumeLogic = slicer.modules.cropvolume.logic()
        # cropVolumeParameterNode = slicer.vtkMRMLCropVolumeParametersNode()
        # cropVolumeParameterNode.SetROINodeID(referenceBoxROINode.GetID())
        # cropVolumeParameterNode.SetVoxelBased(True)
    
        nt = inputSequenceArray.shape[0]
        croppedSequenceVolume = []
        for idt in range(nt):
            # tmpNode = inputVolumeSequence.GetNthDataNode(idt)
            # cropVolumeParameterNode.SetInputVolumeNodeID(inputVolumeSequence.GetNthDataNode(idt).GetID())
            # cropVolumeLogic.Apply(cropVolumeParameterNode)
            # croppedVolumeNode = slicer.mrmlScene.GetNodeByID(cropVolumeParameterNode.GetOutputVolumeNodeID())
            # croppedSequenceVolume.append(slicer.util.arrayFromVolume(croppedVolumeNode))
            croppedSequenceVolume.append(self.cropVolumeFromROI(inputSequenceArray[idt,:,:,:],referenceBoxROINode,referenceScalarVolumeNode))
            # print(f'Centre of the cropped volume: {croppedVolumeNode.GetOrigin()}')
        outputVolumeArray = np.stack(croppedSequenceVolume, axis=0)
        # print(f'Cropped size: {outputVolumeArray.shape}')
        # slicer.mrmlScene.RemoveNode(croppedVolumeNode)
        
        return outputVolumeArray
        
    # JU - Fitting functions (TODO: Explore whether can take some of the implementation in PkModelling and/or Breast_DCEMRI_FTV)
    def simple_linear_fit(self, time_axis, sample_points, norder = 1):
        # simple lin fit: y(t) = m*t + n ==> lin_params = [m_slope, n_coeff]
        lin_params = np.polyfit(time_axis, sample_points, norder)
        yeval = np.polyval(lin_params, time_axis)
        return lin_params, yeval

    def getVolumeDataFromSequence(self, sequenceNode):

        # Fill in the 4D array from the sequence node
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#access-voxels-of-a-4d-volume-as-numpy-array
        nt = sequenceNode.GetNumberOfDataNodes()
        # Size of the numpy array is ordered as [nz, ny(row), nx(col)] TODO: verify row and col are correctly assigned!!
        volume0 = slicer.util.arrayFromVolume(sequenceNode.GetNthDataNode(0))
        [nz, ny, nx] = volume0.shape
        inputVolumeArray = np.zeros([nt, nz, ny, nx]) # JU to follow ITK convention for 4D volumes

        inputVolumeArray[0,:,:,:] = volume0

        for volumeIndex in range(1, nt):
            inputVolumeArray[volumeIndex, :, :, :] = slicer.util.arrayFromVolume(sequenceNode.GetNthDataNode(volumeIndex))
        
        return inputVolumeArray

        
    def subtractVolumes(self, inputSequenceNode, minuendIndex, subtrahendIndex, outputVolumeNode=None):
        
        # if the outputVolume does not exist, creates a new one and returns it:
        if outputVolumeNode is None:
            outputVolumeNode = slicer.modules.volumes.logic().CloneVolume(inputSequenceNode.GetNthDataNode(minuendIndex), "substractionVolumeNode")
            
        minuendVolume = slicer.util.arrayFromVolume(inputSequenceNode.GetNthDataNode(minuendIndex))
        subtrahendVolume = slicer.util.arrayFromVolume(inputSequenceNode.GetNthDataNode(subtrahendIndex))
        # Ensure each volume is float, so the dynamic range is ok to represent the data without clipping it
        subtractedVolume = np.abs(minuendVolume.astype(float) - subtrahendVolume.astype(float))
        
        slicer.util.updateVolumeFromArray(outputVolumeNode, subtractedVolume)
        outputVolumeNode.SetName(f'ABS[Volume({minuendIndex})-Volume({subtrahendIndex})]')
        return outputVolumeNode
        
    def getStatsFromMask(self, volumeMaskNode, segmentID):
        
        # To get Summary statistics use the SegmentStatistics module
        # It returns a dictionary with the statistics corresponding to the segmentID provided
        # To get the complete list of statistics use:
        # import SegmentStatistics
        # SegmentStatistics.SegmentStatisticsLogic().getParameterNode().GetParameterNames()

        import SegmentStatistics

        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", volumeMaskNode.GetID())
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_origin_ras.enabled",str(True))
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_diameter_mm.enabled",str(True))
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_x.enabled",str(True))
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_y.enabled",str(True))
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_z.enabled",str(True))
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()
        outputStats = {}
        for statPlugInName, measurementDetails in stats['MeasurementInfo'].items():
            outputStats[statPlugInName.replace('LabelmapSegmentStatisticsPlugin.','')] = measurementDetails
            outputStats[statPlugInName.replace('LabelmapSegmentStatisticsPlugin.','')]['value'] = stats[segmentID, statPlugInName]
        return outputStats

    # Get ROI coordinates:
    def getBoxROIIJKCoordinates(self, markupROINode, referenceVolumeNode, transformedVolume=False):
        
        markupROI_RAS = self.getRASmarkupROICoordinates(markupROINode)

        # If volume node is transformed, apply that transform to get volume's RAS coordinates
        if transformedVolume:
            transformRasToVolumeRas = vtk.vtkGeneralTransform()
            slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(None, referenceVolumeNode.GetParentTransformNode(), transformRasToVolumeRas)
            
            markupROI_RAS['RASmin'] = transformRasToVolumeRas.TransformPoint(markupROI_RAS['RASmin'])
            markupROI_RAS['RASmax'] = transformRasToVolumeRas.TransformPoint(markupROI_RAS['RASmax'])
        
        markupROI_IJK_inRefVol = self.convertRAStoIJKVolumeNodeCoordinates(markupROI_RAS, referenceVolumeNode)
        
        return markupROI_IJK_inRefVol
    
    def getRASmarkupROICoordinates(self, markupBoxROINode):
        
        boundingBoxRASCoordinates = np.zeros(6)
        markupBoxROINode.GetBounds(boundingBoxRASCoordinates)
        # if DEBUG_mode
        # print(f'ROI coordinates: {boundingBoxRASCoordinates}')
        # Get BOX corners in RAS:
        bbox_rmin, bbox_rmax, bbox_amin, bbox_amax, bbox_smin, bbox_smax = boundingBoxRASCoordinates
        outputRAS = {'RASmin': [bbox_rmin, bbox_amin, bbox_smin],
                        'RASmax': [bbox_rmax, bbox_amax, bbox_smax]}
        
        return outputRAS
    
    def convertRAStoIJKVolumeNodeCoordinates(self, RAScoordinatesDict, referenceVolumeNode):
        
        volumeSize = referenceVolumeNode.GetImageData().GetDimensions() # IJK
        bbox_ijk = np.ones((2,4))#, dtype=int)
        referenceDimensions = np.full_like(bbox_ijk, np.append(volumeSize,2), dtype=int) - 1
        
        volumeRasToIjk = vtk.vtkMatrix4x4()
        referenceVolumeNode.GetRASToIJKMatrix(volumeRasToIjk)
        volumeRasToIjk.MultiplyPoint(np.append(RAScoordinatesDict['RASmin'], 1.0), bbox_ijk[0,:])
        # if DEBUG_mode
        # print(f"ROI upper corner: [{','.join([f'{int(ijk)}' for ijk in bbox_ijk[0,:]])}]")

        volumeRasToIjk.MultiplyPoint(np.append(RAScoordinatesDict['RASmax'], 1.0), bbox_ijk[1,:])
        # if DEBUG_mode
        # print(f"ROI lower corner: [{','.join([f'{int(ijk)}' for ijk in bbox_ijk[1,:]])}]")
        
        # Round the elements and convert them to integer:
        bbox_ijk = bbox_ijk.round().astype(int)
        # In case any coordinate is outside the volume, set it to 0 or max:
        bbox_ijk[bbox_ijk < 0] = 0
        outsideIndices = ( bbox_ijk > referenceDimensions )
        bbox_ijk[outsideIndices] = referenceDimensions[outsideIndices]
        
        outputIJK = {'IJKmin': np.min(bbox_ijk[:,:-1], axis=0),
                        'IJKmax': np.max(bbox_ijk[:,:-1], axis=0)+1}
        # if DEBUG_mode
        # print(f'ROI corner fitted into the volume: {outputIJK}')
        return outputIJK
    
    def getBoxROIOriginCoordinates(self, markupBoxROINode):
        
        roiDiameter = markupBoxROINode.GetSize()
        roiOrigin_Roi = [-roiDiameter[0]/2, -roiDiameter[1]/2, -roiDiameter[2]/2, 1]
        roiToRas = markupBoxROINode.GetObjectToWorldMatrix()
        roiOrigin_Ras = roiToRas.MultiplyPoint(roiOrigin_Roi)
        # These are meant to be used in any volumeNode that we can translate into the markup ROI coordinates:
        #  scalarVolumeNode.SetIJKToRASDirections(roiToRas.GetElement(0,0), roiToRas.GetElement(0,1), roiToRas.GetElement(0,2), roiToRas.GetElement(1,0), roiToRas.GetElement(1,1), roiToRas.GetElement(1,2), roiToRas.GetElement(2,0), roiToRas.GetElement(2,1), roiToRas.GetElement(2,2))
        #  scalarVolumeNode.SetOrigin(roiOrigin_Ras[0:3])

        return roiToRas, roiOrigin_Ras
    
    def translateVolumeToROIBox(self, volumeNodeToTranslate, markupBoxROINode):
        
        roi2RAS, roiOrigin_RAS = self.getBoxROIOriginCoordinates(markupBoxROINode)
        volumeNodeToTranslate.SetIJKToRASDirections(roi2RAS.GetElement(0,0), roi2RAS.GetElement(0,1), roi2RAS.GetElement(0,2), roi2RAS.GetElement(1,0), roi2RAS.GetElement(1,1), roi2RAS.GetElement(1,2), roi2RAS.GetElement(2,0), roi2RAS.GetElement(2,1), roi2RAS.GetElement(2,2))
        volumeNodeToTranslate.SetOrigin(roiOrigin_RAS[0:3])

        return volumeNodeToTranslate
    
    def fitBoxROImarkupToVolume(self, referenceVolumeNode, markupROINode):
        
        cropVolumeParameters = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLCropVolumeParametersNode")
        cropVolumeParameters.SetInputVolumeNodeID(referenceVolumeNode.GetID())
        cropVolumeParameters.SetROINodeID(markupROINode.GetID())
        slicer.modules.cropvolume.logic().SnapROIToVoxelGrid(cropVolumeParameters)  # optional (rotates the ROI to match the volume axis directions)
        slicer.modules.cropvolume.logic().FitROIToInputVolume(cropVolumeParameters)
        slicer.mrmlScene.RemoveNode(cropVolumeParameters)        
        
    # def setParametricMapsVolumeSequence(self, volumeNode, )
    # JU - This may be useful to define the table and labels:
    # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#create-color-table-node
    # JU - End of user-defined section

    def process(self,
                inputVolumeSequenceNode: vtkMRMLSequenceNode, #vtkMRMLScalarVolumeNode,
                maskVolumeSegmentationNode: vtkMRMLSegmentationNode, #vtkMRMLScalarVolumeNode,
                outputMapsSequenceNode: vtkMRMLSequenceNode,
                outputLabelMapVolumeNode: vtkMRMLLabelMapVolumeNode,
                referenceBoxROINode: vtkMRMLMarkupsROINode, # Add roi Box as input argument!
                tableNodeDict: dict={'TableName': [vtkMRMLTableNode, 'label_list']}, #vtkMRMLTableNode,
                preContrastIndex: int=0,
                earlyPostContrastIndex: int=1,
                latePostContrastIndex: int=-1,
                timings: dict={},
                PEthreshold: float=70.0,
                SERthreshold: float=1.4,
                BKGRNDthreshold: float=60.0,
                segmentNodeID: str='', 
                ) -> None:
        """
        TODO: Update description of the input parameters
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolumeSequenceNode or not maskVolumeSegmentationNode:
            raise ValueError("Input or output volume is invalid")
        
        if preContrastIndex == earlyPostContrastIndex:
            raise ValueError("Pre Contrast Index Cannot be the same as the Early Post Contrast")
        
        if earlyPostContrastIndex == latePostContrastIndex:
            
            ok = slicer.util.confirmYesNoDisplay("Early and Late Post Contrast indices are the same. Shall we continue?", windowTitle="WARNING")
            if not ok:
                return
            
        # import time

        # startTime = time.perf_counter()
        # logging.info("Processing started")
        
        # Get input volume dimensions
        inputVolume4Darray = self.getVolumeDataFromSequence(inputVolumeSequenceNode)
        [nt, nz, nx, ny] = inputVolume4Darray.shape

        # Allocate space in TICtable for the intensity values from the DCE array
        time_intensity_curve = np.full((nt, len(tableNodeDict['TICTable'][1])), np.nan)
        time_intensity_curve[:,0] = np.linspace(0, nt, nt, endpoint=False) 
        if timings is not None:
            print(f"Time Points: {timings['timepoints']}")
            time_intensity_curve[:, 0] = timings['timepoints'] / (1000 * 60) # From ms to min
        
        # JU - Create temporary volumes to work with inside this function:
        # Pre-populate it with the info from the first input volume in the input sequence, so we get the same image orientation,dimensions, etc.:
        tempReferenceVolumeNode = slicer.modules.volumes.logic().CloneVolume(inputVolumeSequenceNode.GetNthDataNode(0), "temporary")        
        tempSERVolumeNode = slicer.modules.volumes.logic().CloneVolume(inputVolumeSequenceNode.GetNthDataNode(0), "serMap")        
        tempPEVolumeNode  = slicer.modules.volumes.logic().CloneVolume(inputVolumeSequenceNode.GetNthDataNode(0), "peMap")        
        
        roiIJK = self.getBoxROIIJKCoordinates(referenceBoxROINode, tempReferenceVolumeNode)

        # MIP to be used as the backgdround image for the maps and set up a global threshold from the pre-contrast image
        mip_volume = np.max(inputVolume4Darray, axis=0)
        slicer.util.updateVolumeFromArray(tempReferenceVolumeNode, mip_volume)
        outputMapsSequenceNode.SetDataNodeAtValue(tempReferenceVolumeNode, "MIP")
        
        SERmapTemplate = np.zeros((nz,ny,nx))
        PEmapTemplate  = np.zeros((nz,ny,nx))
        
        # Get the segment selected by the list "Segment Label Mask":
        maskSegmentation = maskVolumeSegmentationNode.GetSegmentation()
        # Before doing anything, loop over the segmentation list and delete all labels created locally by this function in previous runs:
        self.resetSegmentList(maskVolumeSegmentationNode, items_to_remove=self.SERlegend)
                    
        # for segment_iID in maskSegmentation.GetSegmentIDs():
        #     segment_i = maskSegmentation.GetSegment(segment_iID)
        #     if segment_i.GetName() in self.SERlegend:
        #         maskSegmentation.RemoveSegment(segment_i)
        
        # Ensure visibility for the selected segment is ON (TRUE)
        selectedSegment = maskSegmentation.GetSegment(segmentNodeID)
        maskDisplayNode = maskVolumeSegmentationNode.GetDisplayNode()
        maskDisplayNode.SetSegmentVisibility(segmentNodeID, True)
        # Load the label map and check whether is empty or not. If empty, then use the ROI markup as the label map:
        label = slicer.util.arrayFromSegmentBinaryLabelmap(maskVolumeSegmentationNode, segmentNodeID)
        if not label.any():
            # the selected mask is empty --> use the ROI markup box only
            # print(f'Label Map is empty. Using the ROI markup box')
            # Get ROI box as nd binary array:
            voi_mask = np.zeros((nz, ny, nx))
            voi_mask[roiIJK['IJKmin'][2]:roiIJK['IJKmax'][2], roiIJK['IJKmin'][1]:roiIJK['IJKmax'][1], roiIJK['IJKmin'][0]:roiIJK['IJKmax'][0]] = 1
            
            slicer.util.updateSegmentBinaryLabelmapFromArray(voi_mask, maskVolumeSegmentationNode, segmentNodeID)
            label = slicer.util.arrayFromSegmentBinaryLabelmap(maskVolumeSegmentationNode, segmentNodeID)
            selectedSegment.SetName('Segment from ROI')
                
        # Crop the volumes before doing any calculation 
        # TODO: Cropping might not have any effect in the efficiency, as I'm processing over the valid voxels only, 
        #       as defined by the ROI markup or user-defined segmentation mask
        # TODO: For some unknown reason, even when cropping "manually" using the indices, the output maps get rotated around the ROI box corner (apparently)
        #       Fortunately, the time to process the whole volume is not that critical at this stage, so can live without cropping
        croppingVolumes = True
        if croppingVolumes:
            # Crop the volumes using the ROI box:
            # label = self.cropVolumeFromROI(label, referenceBoxROINode, tempReferenceVolumeNode)
            # inputVolume4Darray = self.cropSequenceVolumeFromROI(inputVolume4Darray, referenceBoxROINode, tempReferenceVolumeNode)
            inputVolume4Darray = inputVolume4Darray[:, roiIJK['IJKmin'][2]:roiIJK['IJKmax'][2], roiIJK['IJKmin'][1]:roiIJK['IJKmax'][1], roiIJK['IJKmin'][0]:roiIJK['IJKmax'][0]]
            label = label[roiIJK['IJKmin'][2]:roiIJK['IJKmax'][2], roiIJK['IJKmin'][1]:roiIJK['IJKmax'][1], roiIJK['IJKmin'][0]:roiIJK['IJKmax'][0]]
            # update origin to the cropped volume:
            # temporaryVolumeNode = self.translateVolumeToROIBox(temporaryVolumeNode, referenceBoxROINode)
        
        # print(''.join(['§']*100))
        # print(f'JU - This are the corners of the ROI box:')
        # print(''.join(['-']*50))
        # print(f"\tSxyz: {roiIJK['IJKmin']}")
        # print(f"\tFxyz: {roiIJK['IJKmax']}")
        # print(f'Number of non-zeroes in the mask: {np.count_nonzero(label)}')
        # print(''.join(['§']*100))
        
        # end_load_4dVol_time = time.perf_counter()
         
        # Represent the data in terms of SER (S(t)/S0(t)). identifying S0 as the pre-contrast index:
        St0 = inputVolume4Darray[preContrastIndex, :, :, :]
        # The background threshold is defined from the masked only
        bckgrnd_thresh = (BKGRNDthreshold/100.0) * np.percentile(St0, 95)
        base_mask = (St0 >= bckgrnd_thresh) &  label

        # print(''.join(['§']*100))
        # print(f'Stats of the St0 data:')
        # print(''.join(['-']*50))
        # print(f'St0 volume size: {St0.shape}')
        # print(f'[Min, Median, Max]: [{np.min(St0):.2f}, {np.median(St0):.2f}, {np.max(St0):.2f}]')
        # print(f'Mean ± Std: {np.mean(St0):.2f} ± {np.std(St0):.2f}')
        # print(f'PCT Value: {BKGRNDthreshold}')
        # print(f'95th Percentile: {np.percentile(St0, 95)}')
        # print(f'Background Threshold: {bckgrnd_thresh}')
        # print(''.join(['§']*100))

        St_minus_St0 = inputVolume4Darray - St0
        
        St1_minus_St0 = St_minus_St0[earlyPostContrastIndex, :, :, :]
        Stn_minus_St0 = St_minus_St0[latePostContrastIndex, :, :, :]
        
        PE = 100 * St1_minus_St0 / ( St0 + self.EPSILON )
        base_mask &= (PE >= PEthreshold)

        PE = np.where(base_mask, PE, 0)

        # print(''.join(['§']*100))
        # print(f'Stats of the PE data:')
        # print(''.join(['-']*50))
        # print(f'PE volume size: {PE.shape}')
        # print(f'NonZero elements: {np.count_nonzero(PE[PE>0])}')
        # print(f'[Min, Median, Max]: [{np.min(PE[PE>0]):.2f}, {np.median(PE[PE>0]):.2f}, {np.max(PE[PE>0]):.2f}]')
        # print(f'Mean ± Std: {np.mean(PE[PE>0]):.2f} ± {np.std(PE[PE>0]):.2f}')
        # print(f'Pre-Contras Index: {preContrastIndex}')
        # print(f'Early Post-Contras Index: {earlyPostContrastIndex}')
        # print(f'Late Post-Contras Index: {latePostContrastIndex}')
        # print(''.join(['§']*100))
        
        PEmapTemplate[roiIJK['IJKmin'][2]:roiIJK['IJKmax'][2], roiIJK['IJKmin'][1]:roiIJK['IJKmax'][1], roiIJK['IJKmin'][0]:roiIJK['IJKmax'][0]] = PE

        slicer.util.updateVolumeFromArray(tempPEVolumeNode, PEmapTemplate)
        outputMapsSequenceNode.SetDataNodeAtValue(tempPEVolumeNode, "PE")
        # Delete tempPEVolumeNode asap:
        slicer.mrmlScene.RemoveNode(tempPEVolumeNode)

        
        SER = ( St1_minus_St0 / ( Stn_minus_St0 + self.EPSILON ) ) 
        SER[SER < 0.0] = 0.0
        SER[SER > self.INF_THRESHOLD] = 0.0
        base_mask &= (SER >= 0.0)

        SER = np.where(base_mask, SER, 0)
        
        # print(''.join(['§']*100))
        # print(f'Stats of the SER data:')
        # print(''.join(['-']*50))
        # print(f'NonZero elements: {np.count_nonzero(SER[SER>0])}')
        # print(f'[Min, Median, Max]: [{np.min(SER[SER>0]):.2f}, {np.median(SER[SER>0]):.2f}, {np.max(SER[SER>0]):.2f}]')
        # print(f'Mean ± Std: {np.mean(SER[SER>0]):.2f} ± {np.std(SER[SER>0]):.2f}')
        # print(''.join(['§']*100))


        # print(''.join(['§']*100))
        # print(f"Stats around BR_PE_MASK:")
        # print(''.join(['-']*50))
        # print(f'NonZero elements: {np.count_nonzero(base_mask)}')
        # print(f'max Value: {np.max(base_mask)} (it must be 1)')
        # print(''.join(['§']*100))

        kernel = np.ones((3,3,3))
        kernel[1,1,1] = 100
        # JU - This convolution is to define the maximum over a neighbourhood
        convbrmask = signal.convolve(base_mask, kernel, mode='same')
        base_mask = (convbrmask >= (100 + self.PIXEL_CONNECTIVITY))
        # print(''.join(['§']*100))
        # print(f'Conn Pix Mask stats:')
        # print(''.join(['-']*50))
        # print(f'Connectivity: {self.PIXEL_CONNECTIVITY}')
        # print(f'Non Zero elements: {np.count_nonzero(base_mask)}')
        # print(f'Mask size: {base_mask.shape}')
        # print(f'Max Value: {np.max(base_mask)}')
        # print(''.join(['§']*100))
        
        # conv_mask = cv2.blur(base_mask.astype(float), (9,9))
        # print(f'MinMeanMax: {[np.min(conv_mask), np.mean(conv_mask), np.max(conv_mask)]}')
        # base_mask = (conv_mask > (np.mean(conv_mask)+2.0*np.std(conv_mask)))

        # Relevant for when adding a user-defined segmentation mask (e.g. Tumour_tissue)
        seg_points = np.where(base_mask)
        
        # print(''.join(['§']*100))
        # print(f'Tumour Mask stats:')
        # print(''.join(['-']*50))
        # print(f'Tumour Mask size: {base_mask.shape}')
        # print(f'Non Zero elements: {np.count_nonzero(base_mask)}')
        # print(f'Mask size: {base_mask.shape}')
        # print(f'Max Value: {np.max(base_mask)}')
        # print(''.join(['§']*100))
        
        # This is executed by ftv_map_gen2 (line 2016 in DCE_TumourMapProcess.py)
        # print(''.join(['§']*100))
        SERmap = np.zeros_like(SER)
        for idx, (lb, ub) in enumerate(zip(self.SERLevelLB, self.SERLevelUB)):
            # print(f'Range: SER[xyz] > {lb} & SER[xyz] <= {ub} - Label: {idx+1} (Colour: {self.SERColourMapDictionary[self.SERlegend[idx]]})')
            # print(f' (Legend: {self.SERlegend[idx]})')
            SERmap[(SER > lb) & (SER <= ub)] = idx+1
        # Add the last element of the interval that makes MaxSER < SER:
        idx = len(self.SERLevelUB)
        SERmap[SER > self.SERLevelUB[-1]] = idx + 1
        SERmap *= base_mask
        # print(f'Range: SER[xyz] > {self.SERLevelUB[-1]} - Label: {idx+1} (Colour: {self.SERColourMapDictionary[self.SERlegend[idx]]})')
        # print(f' (Legend: {self.SERlegend[idx]})')
        # print(''.join(['§']*100))

        SERmapTemplate[roiIJK['IJKmin'][2]:roiIJK['IJKmax'][2], roiIJK['IJKmin'][1]:roiIJK['IJKmax'][1], roiIJK['IJKmin'][0]:roiIJK['IJKmax'][0]] = SERmap
        
        slicer.util.updateVolumeFromArray(tempSERVolumeNode, SERmapTemplate)

        volumes_logic = slicer.modules.volumes.logic()
        volumes_logic.CreateLabelVolumeFromVolume(slicer.mrmlScene, outputLabelMapVolumeNode, tempSERVolumeNode)
        # Import label map into a segmentation:
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(outputLabelMapVolumeNode, maskVolumeSegmentationNode)       
        outputMapsSequenceNode.SetDataNodeAtValue(tempSERVolumeNode, "SER")


        # TODO: Can I make it simpler??
        # FTV map label from SERmap:
        FTVmapVolume = np.where(SERmap > 0, 1.0, 0.0)
        # print(f'Size FTV Volume: {FTVmapVolume.shape}')
        ftvLabelMapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "FTV label")
        slicer.util.updateVolumeFromArray(tempSERVolumeNode, FTVmapVolume)
        volumes_logic.CreateLabelVolumeFromVolume(slicer.mrmlScene, ftvLabelMapVolumeNode, tempSERVolumeNode)
        FTVsegmentName = 'FTV_Total'
        maskVolumeSegmentationNode.GetSegmentation().AddEmptySegment(FTVsegmentName)
        FTVsegmentID = vtk.vtkStringArray()
        FTVsegmentID.InsertNextValue(FTVsegmentName)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(ftvLabelMapVolumeNode, maskVolumeSegmentationNode, FTVsegmentID)
        slicer.mrmlScene.RemoveNode(ftvLabelMapVolumeNode)
        FTVsegmentStats = self.getStatsFromMask(maskVolumeSegmentationNode, 
                                                FTVsegmentName)
        maskVolumeSegmentationNode.RemoveSegment(FTVsegmentName)
        slicer.mrmlScene.RemoveNode(tempSERVolumeNode)

        # JU - This operates over the Selected ROI (e.g. Tumour Tissue)
        uptake_ti = 100 * St_minus_St0 / (St0 + self.EPSILON)
        for time_index in range(nt):
            ser_roi  = uptake_ti[time_index,:,:,:]
            time_intensity_curve[time_index,1] =  ser_roi[seg_points].mean()

        max_ENH = np.max(uptake_ti, axis=0)
        delta_ENH = (uptake_ti[latePostContrastIndex,:,:,:] - uptake_ti[earlyPostContrastIndex,:,:,:])[seg_points]
        first_pass_ENH = uptake_ti[earlyPostContrastIndex,:,:,:][seg_points]
        [m_slope, n_coeff], time_intensity_curve[1:,2] = self.simple_linear_fit(time_intensity_curve[1:,0], time_intensity_curve[1:,1])

        # Statistics for the user-defined Segmentation mask
        segmentStats = self.getStatsFromMask(maskVolumeSegmentationNode, segmentNodeID)
        # # Segment Oriented Bounding Box Diameter 
        maxROIDiameter = {'name': 'ROI longest axis',
                            'value': np.max(segmentStats['obb_diameter_mm']['value']),
                            'units': segmentStats['obb_diameter_mm']['units']}
        # ROI Volume:
        # The value returned by segmentStats is the enclosing box (Vol = prod(OBB_diameter)). 
        # To get the equivalent ellipsoidal volume, the formula is 4pi/3 * prod(OBB_radius)
        # Therefore, we need to multiply Vol by: (0.5)^3 * (4pi/3)
        ellipsoidScale = (0.5**3) * (4/3) * np.pi
        roiVolume = {'name': 'ROI Volume',
                        'value': segmentStats['volume_cm3']['value'] * ellipsoidScale,
                        'units': segmentStats['volume_cm3']['units']}
        print(f"ROI Diameter: {segmentStats['obb_diameter_mm']['value']}")
        print(f"ROI Volume: {segmentStats['volume_mm3']['value']}[mm3]")
        print(f"ROI Volume Ellipsoid: {roiVolume['value']}[cm3]")
        labelColumn = vtk.vtkStringArray()
        labelColumn.SetName(tableNodeDict['SummaryTable'][1][0])
        statsColumn = vtk.vtkDoubleArray()
        statsColumn.SetName(tableNodeDict['SummaryTable'][1][1])
        unitsColumn = vtk.vtkStringArray()
        unitsColumn.SetName(tableNodeDict['SummaryTable'][1][2])
        # Add stats to Summary Table:
        labelColumnContent = ['PE Threshold',
                              'SER Threshold',
                              maxROIDiameter['name'], 
                              roiVolume['name'],
                              'Bolus injection time',
                              'Early Phase Time',
                              'Late Phase Time',
                              'Maximum Enhancement',
                              'Delta Enhancement',
                              'First Pass Enhancement',
                              'Enhancement Slope']
        statsColumnContent = [PEthreshold,
                              SERthreshold,
                              maxROIDiameter['value'], 
                              roiVolume['value'],
                              timings['injectionTime']/(1000*60),
                              time_intensity_curve[earlyPostContrastIndex, 0],
                              time_intensity_curve[latePostContrastIndex, 0],
                              max_ENH[seg_points].mean(), 
                              delta_ENH.mean(), 
                              first_pass_ENH.mean(), 
                              m_slope]
        unitsColumnContent = ['%',
                              '[]',
                              maxROIDiameter['units'], 
                              roiVolume['units'], 
                              'min',
                              'min',
                              'min',
                              '%', 
                              '%', 
                              '%', 
                              '[]']
        for rows in zip(labelColumnContent, statsColumnContent, unitsColumnContent):
            labelColumn.InsertNextValue(rows[0])
            statsColumn.InsertNextValue(rows[1])
            unitsColumn.InsertNextValue(rows[2])

        # Statistics for the SER Label Maps:
        nameColumn = vtk.vtkStringArray()
        nameColumn.SetName(tableNodeDict['SERSummaryTable'][1][0])
        volumeColumn = vtk.vtkDoubleArray()
        volumeColumn.SetName(tableNodeDict['SERSummaryTable'][1][1])
        distColumn = vtk.vtkDoubleArray()
        distColumn.SetName(tableNodeDict['SERSummaryTable'][1][2])

        # Iterate over the segmentation mask and get statistics for each SER label:
        maskSegmentations = maskVolumeSegmentationNode.GetSegmentation()
        FTVstats = [FTVsegmentStats['volume_cm3']['value'], FTVsegmentStats['voxel_count']['value']]
        SERlegendCheck = [True]*len(self.SERlegend)
        for segment_iID in maskSegmentations.GetSegmentIDs():
            segmentName = maskSegmentation.GetSegment(segment_iID).GetName()
            # segmentName = segment_i.GetName()
            if segmentName in self.SERlegend:
                segmentPos = self.SERlegend.index(segmentName)
                segmentStats = self.getStatsFromMask(maskVolumeSegmentationNode, segment_iID)
                # nameColumn.InsertNextValue(segmentName)
                # volumeColumn.InsertNextValue(segmentStats['volume_cm3']['value'])
                # distColumn.InsertNextValue(100 * segmentStats['voxel_count']['value'] / FTVstats[1])
                nameColumn.InsertValue(segmentPos, segmentName)
                volumeColumn.InsertValue(segmentPos, segmentStats['volume_cm3']['value'])
                distColumn.InsertValue(segmentPos, 100 * segmentStats['voxel_count']['value'] / FTVstats[1])
                SERlegendCheck[segmentPos] = False
        for idx in range(len(self.SERlegend)):
            if SERlegendCheck[idx]:
                nameColumn.InsertValue(idx, self.SERlegend[idx])
                volumeColumn.InsertValue(idx, 0.0)
                distColumn.InsertValue(idx, 0.0)
                
        # nameColumn.InsertNextValue('FTV (Total Volume)')
        # volumeColumn.InsertNextValue(FTVsegmentStats['volume_cm3']['value'])
        # distColumn.InsertNextValue(100 * FTVsegmentStats['voxel_count']['value']/FTVstats[1])
        nameColumn.InsertValue(len(self.SERlegend), 'FTV (Total Volume)')
        volumeColumn.InsertValue(len(self.SERlegend), FTVsegmentStats['volume_cm3']['value'])
        distColumn.InsertValue(len(self.SERlegend), 100 * FTVsegmentStats['voxel_count']['value']/FTVstats[1])

        # JU - Update table and plot - TODO: I think this should be moved to a different function
        print(f'Updating Table TIC...')
        slicer.util.updateTableFromArray(tableNodeDict['TICTable'][0], time_intensity_curve, tableNodeDict['TICTable'][1])
        print(f'Done updating Table TIC')
        tableNodeDict['SummaryTable'][0].AddColumn(labelColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(statsColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(unitsColumn)
        tableNodeDict['SERSummaryTable'][0].AddColumn(nameColumn)
        tableNodeDict['SERSummaryTable'][0].AddColumn(volumeColumn)
        tableNodeDict['SERSummaryTable'][0].AddColumn(distColumn)

        # Update viewer with results:
        updatedSequenceBrowserNode = self.findBrowserForSequence(outputMapsSequenceNode)
        slicer.modules.sequences.toolBar().setActiveBrowserNode(updatedSequenceBrowserNode)
        # Set background image to be the MIP:
        updatedSequenceBrowserNode.SetSelectedItemNumber(0) # MIP is the first node we added
        self.updateViewer(backgroundVolume=updatedSequenceBrowserNode.GetProxyNode(outputMapsSequenceNode),
                          labelVolume=outputLabelMapVolumeNode)
        self.showVolumeRenderingMIP(updatedSequenceBrowserNode.GetProxyNode(outputMapsSequenceNode))
        # # Import label map into a segmentation:
        # slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(outputLabelMapVolumeNode, maskVolumeSegmentationNode)
        # Add the SER maps to the 3D rendering:
        maskVolumeSegmentationNode.CreateClosedSurfaceRepresentation()
        slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(outputLabelMapVolumeNode)
        # Finally, remove the temporary nodes (it should be wrapped into a try/except/finally statement to ensure it always get deleted)
        slicer.mrmlScene.RemoveNode(tempReferenceVolumeNode)
        
        

# quantificationTest
#


# class quantificationTest(ScriptedLoadableModuleTest):
#     """
#     This is the test case for your scripted module.
#     Uses ScriptedLoadableModuleTest base class, available at:
#     https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
#     """

#     def setUp(self):
#         """Do whatever is needed to reset the state - typically a scene clear will be enough."""
#         slicer.mrmlScene.Clear()

#     def runTest(self):
#         """Run as few or as many tests as needed here."""
#         self.setUp()
#         self.test_quantification1()

#     def test_quantification1(self):
#         """Ideally you should have several levels of tests.  At the lowest level
#         tests should exercise the functionality of the logic with different inputs
#         (both valid and invalid).  At higher levels your tests should emulate the
#         way the user would interact with your code and confirm that it still works
#         the way you intended.
#         One of the most important features of the tests is that it should alert other
#         developers when their changes will have an impact on the behavior of your
#         module.  For example, if a developer removes a feature that you depend on,
#         your test should break so they know that the feature is needed.
#         """

#         self.delayDisplay("Starting the test")

#         # Get/create input data

#         import SampleData

#         registerSampleData()
#         inputVolume = SampleData.downloadSample("quantification1")
#         self.delayDisplay("Loaded test data set")

#         inputScalarRange = inputVolume.GetImageData().GetScalarRange()
#         self.assertEqual(inputScalarRange[0], 0)
#         self.assertEqual(inputScalarRange[1], 695)

#         outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
#         threshold = 100

#         # Test the module logic

#         logic = quantificationLogic()

#         # Test algorithm with non-inverted threshold
#         logic.process(inputVolume, outputVolume, threshold, True)
#         outputScalarRange = outputVolume.GetImageData().GetScalarRange()
#         self.assertEqual(outputScalarRange[0], inputScalarRange[0])
#         self.assertEqual(outputScalarRange[1], threshold)

#         # Test algorithm with inverted threshold
#         logic.process(inputVolume, outputVolume, threshold, False)
#         outputScalarRange = outputVolume.GetImageData().GetScalarRange()
#         self.assertEqual(outputScalarRange[0], inputScalarRange[0])
#         self.assertEqual(outputScalarRange[1], inputScalarRange[1])

#         self.delayDisplay("Test passed")
