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
    parameterPack,
)

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLMarkupsROINode, vtkMRMLLabelMapVolumeNode
from slicer import vtkMRMLSequenceNode, vtkMRMLSegmentationNode, vtkMRMLTableNode
from slicer import qMRMLSegmentEditorWidget, qMRMLSegmentSelectorWidget
# from slicer import vtkMRMLPlotSeriesNode, vtkMRMLPlotChartNode

import numpy as np

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
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Quantification")]
        self.parent.dependencies = ["SequenceRegistration"]  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Jose L. Ulloa (ISANDEX LTD.), Nasib Washal (Queen's Hospital)"] 
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
Slicer Extension to derive non-PK parametric maps from signal intensity analysis of DCE-MRI datasets. 
For up-to-date user guide, go to <a href="https://gthub.com/jlulloaa/..."> official GitHub repository </a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jose L. Ulloa, Nasib Washal. 
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

    # JU - TODO: Is there a better way to implement them?
    preContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices
    earlyPostContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices
    latePostContrastIndex: Annotated[float, WithinRange(0.0, 100.0)] = 0.0 #relevantDCEindices\
    
    # # JU - Simple Checkboxes to control layout view:
    defaultLayoutViewToggle:  bool = True
    renderingLayoutViewToggle:  bool = False

    # # JU - Setting up table and plot nodes (TODO: they are not yet supported by ParameterNodeWrapper)
    # tableTICNode : vtkMRMLTableNode
    # plotTICNode: vtkMRMLPlotSeriesNode
    # # JU - Create chart and add plot (TODO: they are not yet supported by ParameterNodeWrapper)
    # plotChartTICNode: vtkMRMLPlotChartNode

    # # JU - parameters (created automatically by the extension wizard)
    peakEnhancementThreshold: Annotated[float, WithinRange(0.0, 100.0)] = 80.0
    # invertThreshold: bool = False
    # thresholdedVolume: vtkMRMLScalarVolumeNode
    # invertedVolume: vtkMRMLScalarVolumeNode


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
        # To get more help check the code: https://github.com/Slicer/Slicer/blob/main/Libs/MRML/Logic/vtkMRMLLayoutLogic.cxx
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
        self.TICTableRowNames = ["Timepoint", "PE (%)", "Curve Fit"]
        self.SummaryTableRowNames = ["Parameter", "Value", "Units"]
        # JU - Auxiliar nodes
        self.currentVolume = None
        # self.outputVolume = None
        self.segmentID = None
        self.colourTableNode = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/quantification.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        
        # # JU - Create segment editor to get access to effects
        # # JU - To show segment editor widget (useful for debugging): segmentEditorWidget.show()
        self.segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(self.segmentEditorNode)
        self.ui.segmentEditorWidget.enabled = False
        self.ui.segmentEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.ui.segmentEditorWidget.setSegmentationNode(None)
        self.ui.segmentEditorWidget.setSourceVolumeNode(self.currentVolume)
        # JU - Because this widget is not yet supported by the parameters node wrapper, 
        #     the connection to other widgets must be done manually:
        self.ui.segmentEditorWidget.segmentationNodeChanged.connect(self.onSegmentChangeSegmentEditorNode)
        # JU - The same has to be done the other way round, to communicate between inputMaskVolume node to the segmentEditorWidget:
        self.ui.inputMaskSelector.currentNodeChanged.connect(self.onNodeChangeInputMaskSelectorNode)
        # JU - Add a connection to monitor changes in the inputSelector to let segment editor widget knows when to get activated
        self.ui.inputSelector.currentNodeChanged.connect(self.onSequenceChangeInputSelectorNode)
        # JU - This connection manages the visibility of the segment mask
        self.ui.segmentSelectorWidget.currentSegmentChanged.connect(self.updateSelectedSegmentMask)
        
        # JU - Output table selector - 
        # TODO: Check how to do it with parameter node wrapper, would that be easier?
        # TODO: Create a sequence containing each table, that way we could add more tables on the fly
        self.outputTICTableSelector = slicer.qMRMLNodeComboBox()
        self.outputTICTableSelector.noneDisplay = _("Create new table")
        self.outputTICTableSelector.setMRMLScene(slicer.mrmlScene)
        self.outputTICTableSelector.nodeTypes = ["vtkMRMLTableNode"]
        self.outputTICTableSelector.enabled = False
        self.outputTICTableSelector.addEnabled = False
        self.outputTICTableSelector.selectNodeUponCreation = True
        self.outputTICTableSelector.renameEnabled = False
        self.outputTICTableSelector.removeEnabled = False
        self.outputTICTableSelector.noneEnabled = False
        self.outputTICTableSelector.setToolTip(_("Select a Table"))
        self.outputTICTableSelector.setCurrentNode(None)
        # use insertRow to append the new element into a specific row (i.e. FormLayout.insertRow(position, Text, Table))
        # self.ui.outputsFormLayout.addRow(_("Output tables:"), self.outputTICTableSelector)
        # self.ui.parametersGridLayout.addItem(2, _("Output tables:"), self.outputTICTableSelector)
        self.ui.outputGridLayout.addWidget(self.outputTICTableSelector, 2, 1, 1)
        
        
        # JU - Initialise plot series and chart nodes:
        # self.plotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
        self.plotChartNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotChartNode")
        
        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = quantificationLogic()
        
        
        # JU - Initialise colourmap for SER values. 
        # Has to move it away from the init section to after creating the quantificationLogic object, 
        # so can define a function to allow synchronise quickly any change in the intervals and/or colour codes
        # TODO: May be later on we can add it as part of the configurable parameters in the GUI
        self.ser_segment_labels = self.logic.getSERColourMapDict()

        # Connections
        # JU - Here there are only the connections that aren't made automatically by the Parameter node wrapper
        # JU - Any change in the selected index defining the DCE timepoints of interest, 
        # will be reflected as a change in the visualisation:
        
        # JU - Because I want to display/set the current view to whatever slider is moved, I thinks a connector is required:
        self.ui.indexSliderPreContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)
        self.ui.indexSliderEarlyPostContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)
        self.ui.indexSliderLatePostContrast.connect("valueChanged(double)", self.setCurrentVolumeFromIndex)

        # JU - Connect the output table to ensure it gets updated whenever the Apply buttons is pressed:
        # TODO: Delete if no longer needed
        # self.outputTableSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onNodeSelectionChanged)

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

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

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.input4DVolume:
            firstInputSequenceNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSequenceNode")
            if firstInputSequenceNode:
                self._parameterNode.input4DVolume = firstInputSequenceNode
                # self.inputSeqBrowser = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSequenceBrowserNode")
                # self.inputSeqBrowser.SetAndObserveMasterSequenceNodeID(self._parameterNode.input4DVolume.GetID())
                
        # Initialise the output sequence that'll store the output maps, but only if the input sequence has been defined:
        if (not self._parameterNode.outputSequenceMaps) & (self._parameterNode.input4DVolume is not None):
            self._parameterNode.outputSequenceMaps = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceNode", "OutputSequenceNode")
            # Set the index to be maps names:
            self._parameterNode.outputSequenceMaps.SetIndexName("Maps")
            self._parameterNode.outputSequenceMaps.SetIndexType(1)  # 0: Numeric; 1: Text
            self._parameterNode.outputSequenceMaps.SetIndexUnit("")
            self.outputSeqBrowser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", "OutputSequenceBrowserNode")
            self.outputSeqBrowser.SetAndObserveMasterSequenceNodeID(self._parameterNode.outputSequenceMaps.GetID())
            # JU - Might not need outputVolume
            # if self.outputVolume is None:
            #     print(f'Output Volume')
            #     # If not done before, initialise the output Volume Node with the first volume from the input sequence, so the coordinates are the same
            #     self.outputVolume = slicer.modules.volumes.logic().CloneVolume(self._parameterNode.input4DVolume.GetNthDataNode(0),
            #                                                                    "Output PRM")
            #     self._parameterNode.outputSequenceMaps.SetDataNodeAtValue(self.outputVolume, "0")

        # JU - The previous code makes available the input4DVolume node, otherwise, it still be None
        # Set up the index selector, if there is something in input4DVolume:
        if self._parameterNode.input4DVolume:
            # Wrap all the actions into a function, so can be called from other places (e.g. from setParameterNode)
            self.configureView()
            # Initialise the index slider:
            # JU - DEBUG
            # print(f'Initialise parameter node: Setup Index Selector and Widget status')
            # self.setMaxIndexSelector(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
            # # Everytime the module is reloaded, set the selected node to the early post-contrast index
            # self.setCurrentVolumeFromIndex(self._parameterNode.earlyPostContrastIndex)
            # self.ui.parametersCollapsibleButton.enabled=True
            # self.ui.segmentEditorWidget.enabled = True

        # # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputMaskVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if firstVolumeNode:
                self._parameterNode.inputMaskVolume = firstVolumeNode
            else:
                self._parameterNode.inputMaskVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation Mask")
                # There are no segmentation masks available, so let's create one by default. It'll be attached to the segment editor:
                # self.ui.segmentEditorWidget.setSegmentationNode(slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation Mask"))
                # But keeps the selector disabled until the segmentation has a label map
                # self.ui.inputMaskSelector.enabled = False
        #         # And enable the connection with the segment editor to create a label map:
        #         # self.segmentationListSelector.enabled = True
        # JU - Attach a segmentation mask to the segment editor. I think this will remove the warning message when adding the source volume before the mask
        self.ui.segmentEditorWidget.setSegmentationNode(self._parameterNode.inputMaskVolume)
        
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
        # Select default output nodes if nothing is selected yet to save a few clicks for the user
        # if not self._parameterNode.outputVolume:
        #     firstOutputVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        #     if firstOutputVolumeNode:
        #         self._parameterNode.outputVolume = firstOutputVolumeNode
        # print(f'Colour Table: {self.colourTableNode}')
        ser_labels_colour_table = slicer.mrmlScene.GetNodesByName("SER_labels")
        if (self.colourTableNode is None):
            # colourTableNode does not exist, let see whether the SER_labels colour table already exist
            if ser_labels_colour_table.GetNumberOfItems() > 0:
                # Then assign the existing table:
                self.colourTableNode = ser_labels_colour_table.GetItemAsObject(0)
            else:
                print(f'Creates new colour table node...')
                self.colourTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "SER_labels")
        self.colourTableNode.SetTypeToUser()
        # make the color table selectable in the GUI outside Colors module
        self.colourTableNode.HideFromEditorsOff()
        self.setupColourTable()
        # # Associate the colour table with the label map --> Pay attention to the use cases, because there is an error at some point (not yet clear when though)
        self._parameterNode.outputLabelMap.GetDisplayNode().SetAndObserveColorNodeID(self.colourTableNode.GetID())            

        # Add colour table to the scene:
        # slicer.mrmlScene.AddNode(self.colourTableNode)
        # self.colourTableNode.UnRegister(None)

        # Select default plot and tables nodes, to avoid creating new ones:
        if not self.outputTICTableSelector.currentNode():
            self.TICTableNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLTableNode")
            self.SummaryTableNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLTableNode")
            if not self.TICTableNode:
                self.TICTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "TIC Table")
            # TODO: Check how to assign multiple tables to selector
            if not self.SummaryTableNode:
                self.SummaryTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "Summary Table")
            self.outputTICTableSelector.setCurrentNode(self.SummaryTableNode)

        # if not self.plotSeriesNode:
        numberOfPlotSeriesNode = slicer.mrmlScene.GetNodesByClass("vtkMRMLPlotSeriesNode").GetNumberOfItems()
        if numberOfPlotSeriesNode == 0:
            firstPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "TIC plot")
            secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Curve Fit")
        elif numberOfPlotSeriesNode == 1:
            firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
            secondPlotSeriesNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", "Curve Fit")
        else:
            firstPlotSeriesNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotSeriesNode")
            secondPlotSeriesNode = slicer.mrmlScene.GetNthNodeByClass(1, "vtkMRMLPlotSeriesNode")
            
        self.plotSeriesNode = firstPlotSeriesNode
        self.plotCurveFitNode = secondPlotSeriesNode
        self.plotSeriesNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())
        self.plotCurveFitNode.SetAndObserveTableNodeID(self.TICTableNode.GetID())

        if not self.plotChartNode:
            firstPlotChartNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLPlotChartNode")
            if not firstPlotChartNode:
                firstPlotChartNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", "TIC chart")
            self.plotChartNode = firstPlotChartNode
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotSeriesNode.GetID())
            self.plotChartNode.AddAndObservePlotSeriesNodeID(self.plotCurveFitNode.GetID())
        
        # Finally, (re-)configure the plot window
        self.configurePlotWindow()
     
    def setParameterNode(self, inputParameterNode: Optional[quantificationParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """
        # JU - DEBUGMODE
        print('setParameterNode - Start')
        if self._parameterNode:
            # JU - DEBUGMODE
            # print('Parameter Node is not null. Disconnecting GUI')
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            print(f'Setting up parameters, calling removeObserver...')
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            print(f'Setting up parameters, called removeObserver...')
        # JU - DEBUGMODE
        # print('Setting the parameter Node to input Parameter node')
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # print('Parameter Node is not null. Assigning a Node GUI Tag')
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            if self._parameterNode.input4DVolume:
                self.configureView()
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
                
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.input4DVolume and self._parameterNode.inputMaskVolume and (self.segmentID is not None):
            # Before anything else, check layout selectors:
            self.checkDefaultVieweLayout()
            self.checkVolumeRenderingVieweLayout()
            # JU - DEBUGMODE
            # print("Compute output volume")
            # if self._parameterNode.outputVolume is None:
            # if (slicer.mrmlScene.GetNodesByName("Output PRM").GetNumberOfItems() < 1):
            #     # If not done before, initialise the output Volume Node with the first volume from the input sequence, so the coordinates are the same
            #     print(f'Creating another output map')
            #     self.outputVolume = slicer.modules.volumes.logic().CloneVolume(self._parameterNode.input4DVolume.GetNthDataNode(0),
            #                                                                    "Output PRM")
            # TODO: update legend indicating the index corresponds to the Pre-Contrast phase
            self.setCurrentVolumeFromIndex()#self.ui.indexSliderPreContrast.value)
            self.ui.segmentEditorWidget.setSourceVolumeNode(self.currentVolume)
            # Setup Reference Box ROI
            # # JU - Once tested, reposition this snipet in the right place 
            # referenceSeed = vtk.vtkSphereSource()
            
            # referenceSeed.SetCenter(self.currentVolume.GetOrigin())
            # referenceSeed.SetRadius(20)
            # referenceSeed.Update()
            # self._parameterNode.inputMaskVolume.AddSegmentFromClosedSurfaceRepresentation(referenceSeed.GetOutput(), "Reference", [0.0,0.0,1.0])
            
            self.ui.parametersCollapsibleButton.enabled=True
            self.ui.applyButton.toolTip = _("Compute output volume")
            self.ui.applyButton.enabled = True
            # self.outputTICTableSelector.enabled = True
            # self.ui.segmentEditorWidget.setSegmentationNode(self._parameterNode.inputMaskVolume)
        else:
            # JU - DEBUGMODE
            # print('Nothing to do, will keep the button disabled...')
            self.ui.applyButton.toolTip = _("Select input and mask volumes nodes")
            self.ui.applyButton.enabled = False
            
    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            # Enable Table selection and update chart window:
            # self.plotSeriesNode.SetName(self.ui.segmentListSelector.currentText)
            self.update_plot_window()
            # Compute output
            self.logic.process(self._parameterNode.input4DVolume, 
                               self._parameterNode.inputMaskVolume, 
                               self._parameterNode.outputSequenceMaps, 
                            #    self._parameterNode.outputSequenceMaps.GetNthDataNode(0),
                               self._parameterNode.outputLabelMap,
                               self.roiNode,
                               {'TICTable': [self.TICTableNode, self.TICTableRowNames],
                                'SummaryTable': [self.SummaryTableNode, self.SummaryTableRowNames]}, #outputTICTableSelector.currentNode(),
                               int(self._parameterNode.preContrastIndex), #int(self.ui.indexSliderPreContrast.value), 
                               int(self._parameterNode.earlyPostContrastIndex), # int(self.ui.indexSliderEarlyPostContrast.value), 
                               int(self._parameterNode.latePostContrastIndex), #int(self.ui.indexSliderLatePostContrast.value), #)
                               self._parameterNode.peakEnhancementThreshold,
                               self.segmentID) # self.ui.segmentListSelector.currentIndex,

            # self.logic.updateViewer(volumeToDisplay=self._parameterNode.outputVolume)
            # Compute inverted output (if needed)
            # if self.ui.invertedOutputSelector.currentNode():
            #     # If additional output volume is selected then result with inverted threshold is written there
            #     self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
            #                        self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)
            # slicer.modules.plots.logic().ShowChartInLayout(self.plotChartNode)        

    # JU - user-defined connnector functions
    
    def checkDefaultVieweLayout(self):
        if self._parameterNode.defaultLayoutViewToggle:
            # Force the 3D renderingViewToggle to false:
            self.layoutManager.setLayout(self.customLayoutId)
            self.ui.volumeRenderingViewToggle.setChecked(False)
            
    def checkVolumeRenderingVieweLayout(self):
        if self._parameterNode.renderingLayoutViewToggle:
            # Force the defaultLayoutViewToggle to false:
            # self.ui.volumeRenderingViewToggle = False
            self.layoutManager.setLayout(self.volumeRenderOnlyLayout)
            self.ui.defaultViewToggle.setChecked(False)
        else:
            self.ui.defaultViewToggle.setChecked(True)
            self.layoutManager.setLayout(self.customLayoutId)
            
    def onSegmentChangeSegmentEditorNode(self):
        # print('Changed segment mask from segment editor node...')
        self.ui.inputMaskSelector.setCurrentNode(self.ui.segmentEditorWidget.segmentationNode())
        
    def onNodeChangeInputMaskSelectorNode(self):
        # print('Changed input mask node...')
        self.ui.segmentEditorWidget.setSegmentationNode(self.ui.inputMaskSelector.currentNode())
    
    def onSequenceChangeInputSelectorNode(self):
        # print('Changed the main input selector node...')
        if self._parameterNode is not None:
            self.setCurrentVolumeFromIndex(self._parameterNode.preContrastIndex)
        self.ui.segmentEditorWidget.setSourceVolumeNode(self.currentVolume)
        
    def onInputSelect(self):
        if not self._parameterNode.input4DVolume: #self.ui.inputSelector.currentNode():
            # print('No nodes to use')
            numberOfDataNodes = 0
        else:
            numberOfDataNodes = self._parameterNode.input4DVolume.GetNumberOfDataNodes() #self.ui.inputSelector.currentNode().GetNumberOfDataNodes()
            # JU - DEBUG
            # Get some information of the selected sequence:
            self.ui.segmentEditorCollapsibleButton.enabled = True
            self.segmentationListSelector.enabled = True
        print(f'Number of items in the sequence: {numberOfDataNodes}')
        self.setMaxIndexSelector(numberOfDataNodes)
    
    def updateSelectedSegmentMask(self):
        self.segmentID = self.ui.segmentSelectorWidget.currentSegmentID()
        # print(f'update Selected Segment: {self.segmentID}')
        # # Set visibility for the selected segmentation label:
        # TODO: apparently, if there is only one segmentation, it issues an error
        if self._parameterNode:
            displayNode = self._parameterNode.inputMaskVolume.GetDisplayNode()
            displayNode.SetAllSegmentsVisibility(False) # Hide all segments
            displayNode.SetSegmentVisibility(self.segmentID, True)
        self._checkCanApply()
        # JU - TODO: set viewer to the slice where the roi can be seen (decide if using the first, middle, last or any other relevant for the study)
    
    # JU - User-defined functions
    def configureView(self):
        
        # print(f'Running configureView function')
        self.setMaxIndexSelector(self._parameterNode.input4DVolume.GetNumberOfDataNodes())
        # Everytime the module is reloaded, set the selected node to the early post-contrast index
        self.setCurrentVolumeFromIndex(self._parameterNode.earlyPostContrastIndex)
        self.ui.parametersCollapsibleButton.enabled=True
        self.ui.segmentEditorWidget.enabled = True
        # JU - Add the Reference BOX ROI to crop the analysis:
        self.setupBoxROI()
        # JU - If not done before, enable the segment editor
        self.ui.segmentEditorWidget.enabled = True
    
    def setupBoxROI(self):
        self.roiNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsROINode")
        if self.roiNode is None:
            # setup the ROI
            self.roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "RefBox")
            # JU - Setup a Box ROI to crop the volume of interest. When running this function, the input volume must have been defined:
            # Centre the ROI to the volume on display:
            self.roiNode.SetRadiusXYZ(self.currentVolume.GetOrigin())
            new_roi_bounds = [0]*6
            self.roiNode.GetBounds(new_roi_bounds)
            # TODO: enable a checkbox to control BoxROI visibility
        # print(f'Ensure the display box is hidden...')
        self.roiNode.SetDisplayVisibility(False)

    # JU - separate to refresh the index selctors everytime the module is loaded (not only when the input selector changes)
    def setMaxIndexSelector(self, maxIndex):
        for sequenceItemSelectorWidget in [self.ui.indexSliderPreContrast, self.ui.indexSliderEarlyPostContrast, self.ui.indexSliderLatePostContrast]:
            if maxIndex < 1:
                sequenceItemSelectorWidget.maximum = 0
                sequenceItemSelectorWidget.enabled = False
            else:
                sequenceItemSelectorWidget.maximum = maxIndex-1
                sequenceItemSelectorWidget.enabled = True

        self._parameterNode.preContrastIndex = 0
        self._parameterNode.earlyPostContrastIndex =  1
        self._parameterNode.latePostContrastIndex = sequenceItemSelectorWidget.maximum
        
    def setCurrentVolumeFromIndex(self, indexAsDouble=None):
        sequenceBrowserNode = self.logic.findBrowserForSequence(self._parameterNode.input4DVolume)
        # # JU - DEBUGMODE
        # print(f'Selected Sequence from browser is {sequenceBrowserNode.GetName()}')
        if indexAsDouble is not None:
            sequenceBrowserNode.SetSelectedItemNumber(int(indexAsDouble))
        # self.currentVolume = sequenceBrowserNode.GetProxyNode(self._parameterNode.input4DVolume) #self.ui.inputSelector.currentNode())
        self.currentVolume = sequenceBrowserNode.GetProxyNode(self.ui.inputSelector.currentNode())
        # Update the sequence browser toolbar with the seqeuence selected in the input selector
        slicer.modules.sequences.toolBar().setActiveBrowserNode(sequenceBrowserNode)        
        # # JU - This displays the selected volume in the viewer
        # # (https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#show-a-volume-in-slice-views)
        self.logic.updateViewer(self.currentVolume)
    
    def configurePlotWindow(self):
        # print('Configuring Plot Series and Chart Window...')
        # Configure Plot Series:
        self.plotSeriesNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotSeriesNode.SetYColumnName(self.TICTableRowNames[1])
        self.plotSeriesNode.SetPlotType(self.plotSeriesNode.PlotTypeScatter)
        self.plotSeriesNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        self.plotSeriesNode.SetColor(0, 0.6, 1.0)
        
        # Configure Plot Curve Fit
        self.plotCurveFitNode.SetXColumnName(self.TICTableRowNames[0])
        self.plotCurveFitNode.SetYColumnName(self.TICTableRowNames[2])
        self.plotCurveFitNode.SetPlotType(self.plotCurveFitNode.PlotTypeScatter)
        self.plotCurveFitNode.SetLineStyle(slicer.vtkMRMLPlotSeriesNode.LineStyleSolid)
        self.plotCurveFitNode.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleNone)
        self.plotCurveFitNode.SetColor(0, 0, 0)

        # Configure Plot Chart Window:
        self.plotChartNode.SetTitle("Time Intensity Curves")
        self.plotChartNode.SetXAxisTitle(self.TICTableRowNames[0])
        self.plotChartNode.SetYAxisTitle(self.TICTableRowNames[1])
        self.plotChartNode.LegendVisibilityOn()
        self.plotChartNode.SetXAxisRangeAuto(True)
        self.plotChartNode.SetYAxisRangeAuto(True)
        
        # Assign Plot Series to Chart window:
        # slicer.modules.plots.logic().ShowChartInLayout(self.plotChartNode)        
        plotWidget = self.layoutManager.plotWidget(0)
        self.plotViewNode = plotWidget.mrmlPlotViewNode()
        self.plotViewNode.SetPlotChartNodeID(self.plotChartNode.GetID())
        
        
    def update_plot_window(self):
        # enable TIC table:
        self.outputTICTableSelector.enabled=True
        self.ui.outputsCollapsibleButton.enabled=True
        # display table:
        self.logic.displayTable(self.SummaryTableNode) #outputTICTableSelector.currentNode())
        # It appears that by defining the layout, it is no longer needed to update the chart view
        # TODO: Remove the following line once confirmed 
        # self.logic.displayChart(self.plotChartNode)
        # JU - update plot name according to the selected segment name:
        segmentations = self._parameterNode.inputMaskVolume.GetSegmentation()
        self.plotSeriesNode.SetName(segmentations.GetSegment(self.segmentID).GetName())
    
    def setupColourTable(self):
        nLabels = len(self.ser_segment_labels)
        # print(f'Number of Labels: {nLabels}')
        self.colourTableNode.SetNumberOfColors(nLabels)
        self.colourTableNode.SetNamesInitialised(True) # prevent automatic color name generation
        for idx, (legend, [r,g,b,a]) in enumerate(self.ser_segment_labels.items()):
            success = self.colourTableNode.SetColor(idx, legend, r, g, b, a)
            # if success:
            #     print(f'Legend: {legend}. Well done!!')
            # else:
            #     print(f'Problem with Legend: {legend}')
                         
    def clickToDisplay():
        print('hola')
        

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
        self.EPSILON = 1e-3
        self.INF_THRESHOLD = 1e2
        self.UPPER_ENH_THRESHOLD = 5e2
        self.PIXEL_CONNECTIVITY = 8
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
        ]0.9, 1.0]: Purple (0.5, 0, 0.5)
        ]1.0, 1.3]: Green (0, 1, 0)
        ]1.3, 1.75]: Red (1, 0, 0)
        ]1.75, 3.0]: Yellow (1, 1, 0)
        >0.0 & <3.0 (i.e. No SER): White (1, 1, 1)
        """
        alfa = 1
        serMapInterval = [0.00, 0.90, 1.00, 1.30, 1.75, 3.00]
        # serMapInterval = [0.00, 0.90, 1.00, 1.10]
        serMapColours = [[0.0, 0.0, 1.0, alfa], # blue
                         [0.5, 0.0, 0.5, alfa], # purple
                         [0.0, 1.0, 0.0, alfa], # green
                         [1.0, 0.0, 0.0, alfa], # red
                         [1.0, 1.0, 0.0, alfa], # yellow
                         [0.0, 0.0, 0.0, 0.0] # black & transparent so it can be overlaid with the MIP
                         ]
        # serMapColours = np.array(serMapColours)[[0,2,3,-1]]
        self.SERLevelLB = serMapInterval[:-1]
        self.SERLevelUB = serMapInterval[1:]
        self.SERColourMapDictionary = {'non SER': serMapColours[-1]}
        self.SERlegend = []
        for idx, (lb, ub) in enumerate(zip(self.SERLevelLB, self.SERLevelUB)):
            legend = f'{lb} < SER ≤ {ub}'
            self.SERColourMapDictionary[legend] = serMapColours[idx]
            self.SERlegend.append(legend)

    def getSegmentList(self, maskVolumeNode):

        nsegments = maskVolumeNode.GetSegmentation().GetNumberOfSegments()
        segmentList = [maskVolumeNode.GetSegmentation().GetNthSegment(idx) for idx in range(nsegments)]

        return segmentList

    def displayTable(self, currentTable):
        slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(currentTable.GetID())
        currentTable.SetUseColumnTitleAsColumnHeader(True)  # Make column titles visible (instead of column names)
        slicer.app.applicationLogic().PropagateTableSelection()
            
    def updateViewer(self, backgroundVolume=None, foregroundVolume=None, labelVolume=None, labelOpacity=None):
        
        if foregroundVolume is not None:
            foregroundOpacity=self.FG_OPACITY
            # TODO: Set the name of the background and foreground nodes in display
            for channels in ["Red", "Yellow"]:
                view = slicer.app.layoutManager().sliceWidget(channels).sliceView()
                view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft,foregroundVolume.GetName())
        else:
            foregroundOpacity = None
        
        if labelVolume is not None:
            labelOpacity = self.LB_OPACITY
            colorLegendDisplayNode = slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(labelVolume)
            colorLegendDisplayNode.ScalarVisibilityOn()
            colorLegendDisplayNode.GetLabelTextProperty().SetFontFamilyToArial()
                  
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

    # JU - Crop Volume from ROI Box:
    def cropVolumeFromROI(self, inputVolumeAsArray, referenceBoxROINode):

        # Crop the volumes before doing any calculation:
        auxiliarScalarNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "temporaryVolume")
        slicer.util.updateVolumeFromArray(auxiliarScalarNode, inputVolumeAsArray)
        cropVolumeLogic = slicer.modules.cropvolume.logic()
        cropVolumeParameterNode = slicer.vtkMRMLCropVolumeParametersNode()
        cropVolumeParameterNode.SetROINodeID(referenceBoxROINode.GetID())
        cropVolumeParameterNode.SetInputVolumeNodeID(auxiliarScalarNode.GetID())
        cropVolumeParameterNode.SetVoxelBased(True)
        cropVolumeLogic.Apply(cropVolumeParameterNode)
        croppedVolumeNode = slicer.mrmlScene.GetNodeByID(cropVolumeParameterNode.GetOutputVolumeNodeID())
        croppedVolume = slicer.util.arrayFromVolume(croppedVolumeNode)
        slicer.mrmlScene.RemoveNode(auxiliarScalarNode)
        slicer.mrmlScene.RemoveNode(croppedVolumeNode)
        
        # return croppedVolume
        return inputVolumeAsArray
    
    # JU - Fitting functions (TODO: Explore whether can take some of the implementation in PkModelling and/or Breast_DCEMRI_FTV)
    def simple_linear_fit(self, time_axis, sample_points, norder = 1):
        # simple lin fit: y(t) = m*t + n ==> lin_params = [m_slope, n_coeff]
        lin_params = np.polyfit(time_axis, sample_points, norder)
        yeval = np.polyval(lin_params, time_axis)
        return lin_params, yeval
           
    # def setParametricMapsVolumeSequence(self, volumeNode, )
    # JU - This may be useful to define the table and labels:
    # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#create-color-table-node
    # JU - End of user-defined section

    def process(self,
                inputVolume: vtkMRMLSequenceNode, #vtkMRMLScalarVolumeNode,
                maskVolume: vtkMRMLSegmentationNode, #vtkMRMLScalarVolumeNode,
                outputMaps: vtkMRMLSequenceNode,
                outputLabelMap: vtkMRMLLabelMapVolumeNode,
                referenceBoxROI: vtkMRMLMarkupsROINode, # Add roi Box as input argument!
                tableNodeDict: dict={'TableName': [vtkMRMLTableNode, 'label_list']}, #vtkMRMLTableNode,
                preContrastIndex: int=0,
                earlyPostContrastIndex: int=1,
                latePostContrastIndex: int=-1,
                PEthreshold: float=80.0,
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

        if not inputVolume or not maskVolume:
            raise ValueError("Input or output volume is invalid")
        
        # JU - Create temporary volumes to store the maps, just before sending them to the output sequence:
        # Pre-populate it with the info from the first input volume in the input sequence, so we get the same image orientation,dimensions, etc.:
        outputVolume = slicer.modules.volumes.logic().CloneVolume(inputVolume.GetNthDataNode(0), "temporary")        

        import time

        startTime = time.perf_counter()
        logging.info("Processing started")
        
        # Get the segment selected by the list "Segment Label Mask":
        # print(f'Processing - SegmentNodeID: {segmentNodeID}')
        maskSegmentation = maskVolume.GetSegmentation()
        # Before doing anything, loop over the segmentations and delete the corresponding to the label maps that are created locally by this function:
        for segment_iID in maskSegmentation.GetSegmentIDs():
            segment_i = maskSegmentation.GetSegment(segment_iID)
            if segment_i.GetName() in self.SERlegend:
                maskSegmentation.RemoveSegment(segment_i)
        
        segmentID = maskSegmentation.GetSegment(segmentNodeID) #GetNthSegmentID(segmentNodeIndex)
        segmentName = segmentID.GetName()
        # Ensure visibility for the selected segment is ON (TRUE)
        maskDisplayNode = maskVolume.GetDisplayNode()
        maskDisplayNode.SetSegmentVisibility(segmentNodeID, True) 

        # To get Summary statistics use the SegmentStatistics module
        import SegmentStatistics
        segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
        segStatLogic.getParameterNode().SetParameter("Segmentation", maskVolume.GetID())
        # segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_origin_ras.enabled",str(True))
        segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_diameter_mm.enabled",str(True))
        # segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_x.enabled",str(True))
        # segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_y.enabled",str(True))
        # segStatLogic.getParameterNode().SetParameter("LabelmapSegmentStatisticsPlugin.obb_direction_ras_z.enabled",str(True))
        segStatLogic.computeStatistics()
        stats = segStatLogic.getStatistics()
        # Get Segment volume:
        volume_cm3 = stats[segmentNodeID,"LabelmapSegmentStatisticsPlugin.volume_cm3"]            
        end_proc_mask_time = time.perf_counter()
        # Get Segment Oriented Bounding Box Diameter 
        obb_diameter_mm = np.array(stats[segmentNodeID,"LabelmapSegmentStatisticsPlugin.obb_diameter_mm"])
        maxROIDiameter = np.max(obb_diameter_mm)
        print(f'OBB diameter: {obb_diameter_mm}[mm]')
        # TODO: For now ignore the reference box, until I understand how to use in the cropping context
        
        # JU - DEBUG Mode:
        # print(f'Segment name: {segmentName}')
        # print(f'Pre-Contrast Index: {preContrastIndex}')
        # print(f'Early Post-Contrast Index: {earlyPostContrastIndex}')
        # print(f'Late Post-Contrast Index: {latePostContrastIndex}')

        label = slicer.util.arrayFromSegmentBinaryLabelmap(maskVolume, segmentNodeID)
        points  = np.where( label == 1 )  # or use another label number depending on what you segmented
        # Size of the numpy array is ordered as [nz, ny(row), nx(col)] TODO: verify row and col are correctly assigned!!
        [nz, ny, nx] = slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(0)).shape
        nt = inputVolume.GetNumberOfDataNodes()
        inputVolume4Darray = np.zeros([nt, nz, ny, nx]) # JU to follow ITK convention for 4D volumes
        
        # Fill in the 4D array from the sequence node
        # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#access-voxels-of-a-4d-volume-as-numpy-array
        for volumeIndex in range(nt):
            inputVolume4Darray[volumeIndex, :, :, :] = slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(volumeIndex))
            
        time_intensity_curve = np.full((nt, len(tableNodeDict['TICTable'][1])), np.nan)
        time_intensity_curve[:,0] = np.linspace(0, nt, nt, endpoint=False) # TODO: replace it by te actual sequence timings (e.g. trigger_times)
        # print(f'Volume Size (Nz x Ny x Nx): [{nz} x {ny} x {nx}]')
        end_load_4dVol_time = time.perf_counter()
        
        # MIP Volume
        mip_volume = np.max(inputVolume4Darray, axis=0)
        slicer.util.updateVolumeFromArray(outputVolume, mip_volume)
        outputMaps.SetDataNodeAtValue(outputVolume, "MIP")
        
        # Represent the data in terms of SER (S(t)/S0(t)). identifying S0 as the pre-contrast index:
        St0 = inputVolume4Darray[preContrastIndex, :, :, :]
        # print(f'Volume Size: {S_t0.shape}')
        
        St_minus_St0 = 100 * ( (inputVolume4Darray - St0) / (St0 + self.EPSILON) )
        # print(f'Dynamic image size: {St_minus_St0.shape}')
        St_minus_St0[St_minus_St0 >= self.UPPER_ENH_THRESHOLD] = self.UPPER_ENH_THRESHOLD # It trims upper values too high. Set them to 0, so they don't affect stats
        
        St1_minus_St0 = St_minus_St0[earlyPostContrastIndex, :, :, :]
        Stn_minus_St0 = St_minus_St0[latePostContrastIndex, :, :, :]

        # JU - This operates over the Selected ROI (e.g. Tumour Tissue)
        for time_index in range(nt):
            uptake_ti = St_minus_St0[time_index, :, :, :]# slicer.util.arrayFromVolume(inputVolume.GetNthDataNode(volumeIndex)) 
            ser_roi  = uptake_ti[points] # this will be a list of the label values
            time_intensity_curve[time_index,1] =  ser_roi.mean()

        # JU - PE Calculations
        # Crop the volumes before doing any calculation - But somehow, need to keep the original coordinates to put them back
        # TODO: for now, keep the cropping out of the equation...
        # label = self.cropVolumeFromROI(label, referenceBoxROI)
        # points  = np.where( label == 1 )  # or use another label number depending on what you segmented
        # S_t0 = self.cropVolumeFromROI(S_t0, referenceBoxROI)
        # S_t1 = self.cropVolumeFromROI(S_t1, referenceBoxROI)
        # S_tn = self.cropVolumeFromROI(S_tn, referenceBoxROI)
        PE = np.zeros_like(St1_minus_St0)
        PE[points] = St1_minus_St0[points]
        PE[PE < PEthreshold] = 0.0
        PEnull = np.where(PE <= 0.0)
        
        slicer.util.updateVolumeFromArray(outputVolume, PE)
        outputMaps.SetDataNodeAtValue(outputVolume, "PE")
        
        SER = np.zeros_like(St1_minus_St0)
        SER[points] = ( St1_minus_St0[points] / (Stn_minus_St0[points] + self.EPSILON ) ) 
        SER[PEnull] = 0.0
        SER[SER < 0.0] = 0.0
        SER[SER > self.INF_THRESHOLD] = 0.0

        SERmap = np.zeros_like(SER)
        for idx, (lb, ub) in enumerate(zip(self.SERLevelLB, self.SERLevelUB)):
            SERmap[(SER > lb) & (SER <= ub)] = idx
        
        # Count occurrences within the ROI:
        unique, counts = np.unique(SERmap[SERmap > 0], return_counts=True)
        pcFromCounts = 100 * counts/np.sum(label==1) # np.sum(counts)
        
        slicer.util.updateVolumeFromArray(outputVolume, SERmap)
        volumes_logic = slicer.modules.volumes.logic()
        volumes_logic.CreateLabelVolumeFromVolume(slicer.mrmlScene, outputLabelMap, outputVolume)
        
        # JU - DEBUG Mode:
        # print(f'Upper Threshold: {self.UPPER_ENH_THRESHOLD}')
        # print(f'PE Threshold: {PEthreshold}')
        # print(f'Max PE: {np.max(PE)}')
        
        max_ENH = np.max(St_minus_St0, axis=0)
        delta_ENH = Stn_minus_St0[points] - St1_minus_St0[points]
        first_pass_ENH = St1_minus_St0[points]

        [m_slope, n_coeff], time_intensity_curve[1:,2] = self.simple_linear_fit(time_intensity_curve[1:,0], time_intensity_curve[1:,1])
        # # JU - DEBUG: should match the mean value of LabelStatistics calculation as a double-check
        # print(f'Mean Values: {time_intensity_curve}') 
        labelColumn = vtk.vtkStringArray()
        labelColumn.SetName(tableNodeDict['SummaryTable'][1][0])
        statsColumn = vtk.vtkDoubleArray()
        statsColumn.SetName(tableNodeDict['SummaryTable'][1][1])
        unitsColumn = vtk.vtkStringArray()
        unitsColumn.SetName(tableNodeDict['SummaryTable'][1][2])
        # Add the percentage of label maps:
        for rows in zip(self.SERlegend, pcFromCounts, ['%']*len(self.SERlegend)):
            labelColumn.InsertNextValue(rows[0])
            statsColumn.InsertNextValue(rows[1])
            unitsColumn.InsertNextValue(rows[2])
        # Add all other stats:
        labelColumnContent = ['Maximum ROI Diameter', 'Maximum Enhancement','Delta Enhancement','First Pass Enhancement','Enhancement Slope', 'ROI volume']
        statsColumnContent = [maxROIDiameter, max_ENH[points].mean(), delta_ENH.mean(), first_pass_ENH.mean(), m_slope, volume_cm3]
        unitsColumnContent = ['mm', '%', '%', '%', '[]', 'cm3']
        for rows in zip(labelColumnContent, statsColumnContent, unitsColumnContent):
            labelColumn.InsertNextValue(rows[0])
            statsColumn.InsertNextValue(rows[1])
            unitsColumn.InsertNextValue(rows[2])
            
            

        stopTime = time.perf_counter()
        logging.info(f"Processing completed in {stopTime-startTime:.2f} seconds")
        print(f'Elapsed time to load the masks: {(end_proc_mask_time-startTime):.2f}s')
        print(f'Elapsed time to load 4D volume and get stats: {(end_load_4dVol_time-end_proc_mask_time):.2f}s')
        print(f'Elapsed time for the whole process: {(stopTime - startTime):.2f}s')
        # JU - Update table and plot - TODO: I think this should be moved to a different function
        slicer.util.updateTableFromArray(tableNodeDict['TICTable'][0], time_intensity_curve, tableNodeDict['TICTable'][1])
        tableNodeDict['SummaryTable'][0].AddColumn(labelColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(statsColumn)
        tableNodeDict['SummaryTable'][0].AddColumn(unitsColumn)

        # Update viewer with results:
        updatedSequenceBrowserNode = self.findBrowserForSequence(outputMaps)
        slicer.modules.sequences.toolBar().setActiveBrowserNode(updatedSequenceBrowserNode)
        # Set background image to be the MIP:
        updatedSequenceBrowserNode.SetSelectedItemNumber(0) # MIP is the first node we added
        self.updateViewer(backgroundVolume=updatedSequenceBrowserNode.GetProxyNode(outputMaps),
                          labelVolume=outputLabelMap)
        self.showVolumeRenderingMIP(updatedSequenceBrowserNode.GetProxyNode(outputMaps))
        # Import label map into a segmentation:
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(outputLabelMap, maskVolume)
        # Add the SER maps to the 3D rendering:
        maskVolume.CreateClosedSurfaceRepresentation()
        slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(outputLabelMap)
        # Finally, remove the temporary node (it should be wrapped into a try/except/finally statement to ensure it always get deleted)
        slicer.mrmlScene.RemoveNode(outputVolume)
        
        

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
