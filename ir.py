#   _____ _              __ _     _     
#  / ____| |            / _(_)   | |    
# | (___ | |_ __ _ _ __| |_ _ ___| |__  
#  \___ \| __/ _` | '__|  _| / __| '_ \ 
#  ____) | || (_| | |  | | | \__ \ | | |
# |_____/ \__\__,_|_|  |_| |_|___/_| |_|
#                                       

import Tkinter as tk
import tkFileDialog

import csv
import numpy as np
from scipy.interpolate import interp1d

from pyne.material import Material
from pyne.xs.data_source import EAFDataSource
from pyne.bins import pointwise_collapse
from pyne.transmute.chainsolve import Transmuter
from pyne import nucname
from pyne.data import decay_const, atomic_mass, gamma_photon_intensity, gamma_energy, beta_intensity, beta_average_energy

import parsedatetime as pdt
import datetime

# Created summer 2017 by Benjamin Morrison '17 (benmorrison@unm.edu or geek@geekanddad.com)

class IRApplication(tk.Frame):
	def __init__(self, master=None):
		# Set up the window object - see http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html for a good explanation of how all the Tk widgets we use work
		tk.Frame.__init__(self, master)
		# Set up window-resizing
		top=self.winfo_toplevel()
		top.rowconfigure(0, weight=1)
		self.rowconfigure(1, weight = 1)
		self.grid(sticky=tk.N+tk.S+tk.E+tk.W)
		# Create all our UI objects
		self.createWidgets()
		# Create variables to store our data
		self.material = None
		self.flux = None
		self.product = None
		self.bq = True
	def createWidgets(self):
		# Tab Bar
		self.tabBar = tk.Frame(self)
		self.setupButton = tk.Button(self.tabBar, text="Setup", command=self.switchPanelSetup)
		self.setupButton.grid(row=0, column=0)
		self.doseButton = tk.Button(self.tabBar, text="Dose (mR/h)", command=self.switchPanelDose)
		self.doseButton.grid(row=0, column=1)
		self.activityButtonC = tk.Button(self.tabBar, text="Activity (mCi)", command=self.switchPanelActivityCi)
		self.activityButtonC.grid(row=0, column=2)
		self.activityButtonB = tk.Button(self.tabBar, text="Activity (Bq)", command=self.switchPanelActivityBq)
		self.activityButtonB.grid(row=0, column=3)
		self.gammasButton = tk.Button(self.tabBar, text="Gamma Energies", command=self.switchPanelGammas)
		self.gammasButton.grid(row=0, column=4)
		self.betasButton = tk.Button(self.tabBar, text="Beta Energies", command=self.switchPanelBetas)
		self.betasButton.grid(row=0, column=5)
		self.quitButton = tk.Button(self.tabBar, text="Quit", command=self.quit)
		self.quitButton.grid(row=0, column=6)
		self.tabBar.grid(row=0, column=0)
		
		# Setup Panel
		self.panelSetup = tk.Frame(self)
		self.powerLabel = tk.Label(self.panelSetup, text="Power (kW)")
		self.powerLabel.grid(row=0, column=0)
		self.powerVar = tk.StringVar()
		self.powerBox = tk.Entry(self.panelSetup, textvariable=self.powerVar)
		self.powerBox.grid(row=0, column=1)
		self.profileLabel = tk.Label(self.panelSetup, text="Flux Profile")
		self.profileLabel.grid(row=0, column=2)
		self.profileVar = tk.StringVar()
		self.profileBox = tk.Entry(self.panelSetup, textvariable=self.profileVar)
		self.profileBox.bind('<Button-1>', self.locateFluxProfile)
		self.profileBox.grid(row=0, column=3)
		self.timeLabel = tk.Label(self.panelSetup, text="Time (enter w, d, h, m, s)")
		self.timeLabel.grid(row=1, column=0)
		self.timeVar = tk.StringVar()
		self.timeBox = tk.Entry(self.panelSetup, textvariable=self.timeVar)
		self.timeBox.grid(row=1, column=1)
		self.massLabel = tk.Label(self.panelSetup, text="Mass (g)")
		self.massLabel.grid(row=1, column=2)
		self.massVar = tk.StringVar()
		self.massBox = tk.Entry(self.panelSetup, textvariable=self.massVar)
		self.massBox.grid(row=1, column=3)
		self.elementTable = tk.Frame(self.panelSetup)
		self.elementLabel = tk.Label(self.elementTable, text="Element/Isotope")
		self.elementLabel.grid(row=0, column=0)
		self.ratioTypeVar = tk.StringVar()
		self.ratioTypeVar.set('Mass Ratio')
		self.ratioMenu = tk.OptionMenu(self.elementTable, self.ratioTypeVar, 'Mass Ratio', 'Number Ratio')
		self.ratioMenu.grid(row=0, column=1)
		self.elementTable.grid(row=2, column=0, columnspan=4)
		self.elementRows = [] # Will eventually be filled with UI widgets, in addElementRow
		self.addElementRow() # And by eventually, I mean immediately, as we set up the first blank row here
		self.addElementButton = tk.Button(self.panelSetup, text = "Add Element", command = self.addElementRow)
		self.addElementButton.grid(row=3, column=0, columnspan = 4)
		self.panelSetup.grid(row=1, column=0)
		
		# Dose Panel
		self.panelDose = tk.Frame(self)
		self.canvasDose = tk.Canvas(self.panelDose) # These next several lines set up scrolling for the Dose panel.
		self.canvasDose.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.dScrollY = tk.Scrollbar(self.panelDose, orient=tk.VERTICAL, command=self.canvasDose.yview)
		self.dScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.dScrollX = tk.Scrollbar(self.panelDose, orient=tk.HORIZONTAL, command=self.canvasDose.xview)
		self.dScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasDose['xscrollcommand'] = self.dScrollX.set
		self.canvasDose['yscrollcommand'] = self.dScrollY.set
		self.winDose = tk.Frame(self)
		self.winDoseID = self.canvasDose.create_window(0, 0, anchor = tk.NW, window = self.winDose) # End scrolling setup
		self.dEOBLabel = tk.Label(self.winDose, text = "Gamma - End of Bombardment - Beta") # Create the various UI objects in the actual panal
		self.dEOBLabel.grid(row = 0, column = 0, columnspan = 3)
		self.dDelayPane = tk.Frame(self.winDose)
		self.dDelayLabel = tk.Label(self.dDelayPane, text = "Gamma - After - Beta")
		self.dDelayLabel.grid(row = 0, column = 0)
		self.delayVar = tk.StringVar()
		self.dDelayBox = tk.Entry(self.dDelayPane, textvariable = self.delayVar)
		self.dDelayBox.grid(row = 0, column = 1)
		self.dDelayPane.grid(row = 0, column = 3, columnspan = 2)
		self.productRows = [] # Will eventually be filled with UI widgets, in addProductRow
		self.winDose.update_idletasks() # Tell Tk to recalculate layout
		self.canvasDose['width'] = self.canvasDose.bbox(self.winDoseID)[2] # and adjust the scrolling appropriately
		self.canvasDose['scrollregion'] = self.canvasDose.bbox(self.winDoseID)
		self.panelDose.rowconfigure(0, weight = 1)
		self.panelDose.columnconfigure(0, weight = 1)
		
		# Activity Panel
		self.panelActivity = tk.Frame(self)
		self.canvasActivity = tk.Canvas(self.panelActivity) # These next several lines set up scrolling for the Dose panel.
		self.canvasActivity.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W) # The structure of the Dose/Activity/Gammas panels are essentially identical.
		self.aScrollY = tk.Scrollbar(self.panelActivity, orient=tk.VERTICAL, command=self.canvasActivity.yview)
		self.aScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.aScrollX = tk.Scrollbar(self.panelActivity, orient=tk.HORIZONTAL, command=self.canvasActivity.xview)
		self.aScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasActivity['xscrollcommand'] = self.aScrollX.set
		self.canvasActivity['yscrollcommand'] = self.aScrollY.set
		self.winActivity = tk.Frame(self)
		self.winActivityID = self.canvasActivity.create_window(0, 0, anchor = tk.NW, window = self.winActivity)
		self.aEOBLabel = tk.Label(self.winActivity, text = "End of Bombardment")
		self.aEOBLabel.grid(row = 0, column = 0, columnspan = 2)
		self.aDelayPane = tk.Frame(self.winActivity)
		self.aDelayLabel = tk.Label(self.aDelayPane, text = "After")
		self.aDelayLabel.grid(row = 0, column = 0)
		self.aDelayBox = tk.Entry(self.aDelayPane, textvariable = self.delayVar)
		self.aDelayBox.grid(row = 0, column = 1)
		self.aDelayPane.grid(row = 0, column = 2)
		self.canvasActivity['width'] = self.canvasActivity.bbox(self.winActivityID)[2]
		self.canvasActivity['scrollregion'] = self.canvasActivity.bbox(self.winActivityID)
		self.panelActivity.rowconfigure(0, weight = 1)
		self.panelActivity.columnconfigure(0, weight = 1)
		
		# Gammas Panel
		self.panelGammas = tk.Frame(self)
		self.canvasGammas = tk.Canvas(self.panelGammas)
		self.canvasGammas.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.gScrollY = tk.Scrollbar(self.panelGammas, orient=tk.VERTICAL, command=self.canvasGammas.yview)
		self.gScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.gScrollX = tk.Scrollbar(self.panelGammas, orient=tk.HORIZONTAL, command=self.canvasGammas.xview)
		self.gScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasGammas['xscrollcommand'] = self.gScrollX.set
		self.canvasGammas['yscrollcommand'] = self.gScrollY.set
		self.winGammas = tk.Frame(self)
		self.winGammasID = self.canvasGammas.create_window(0, 0, anchor = tk.NW, window = self.winGammas)
		self.thresholdLabel = tk.Label(self.winGammas, text = "Threshold")
		self.thresholdLabel.grid(row = 0, column = 0, columnspan = 2)
		self.thresholdVar = tk.StringVar()
		self.thresholdBox = tk.Entry(self.winGammas, textvariable = self.thresholdVar)
		self.thresholdBox.grid(row = 0, column = 2)
		self.isotopeLabel = tk.Label(self.winGammas, text = "Isotope")
		self.isotopeLabel.grid(row = 1, column = 0)
		self.gammaLabel = tk.Label(self.winGammas, text = "Gamma Energy (keV)")
		self.gammaLabel.grid(row = 1, column = 1)
		self.branchLabel = tk.Label(self.winGammas, text = "Branching Ratio")
		self.branchLabel.grid(row = 1, column = 2)
		self.gammaRows = [] # Will eventually be filled with UI widgets, in addGammaRow
		self.canvasGammas['width'] = self.canvasGammas.bbox(self.winGammasID)[2]
		self.canvasGammas['scrollregion'] = self.canvasGammas.bbox(self.winGammasID)
		self.panelGammas.rowconfigure(0, weight = 1)
		self.panelGammas.columnconfigure(0, weight = 1)

		# Betas Panel
		self.panelBetas = tk.Frame(self)
		self.canvasBetas = tk.Canvas(self.panelBetas)
		self.canvasBetas.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.bScrollY = tk.Scrollbar(self.panelBetas, orient=tk.VERTICAL, command=self.canvasBetas.yview)
		self.bScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.bScrollX = tk.Scrollbar(self.panelBetas, orient=tk.HORIZONTAL, command=self.canvasBetas.xview)
		self.bScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasBetas['xscrollcommand'] = self.bScrollX.set
		self.canvasBetas['yscrollcommand'] = self.bScrollY.set
		self.winBetas = tk.Frame(self)
		self.winBetasID = self.canvasBetas.create_window(0, 0, anchor = tk.NW, window = self.winBetas)
		self.bThresholdLabel = tk.Label(self.winBetas, text = "Threshold")
		self.bThresholdLabel.grid(row = 0, column = 0, columnspan = 2)
		self.bThresholdBox = tk.Entry(self.winBetas, textvariable = self.thresholdVar)
		self.bThresholdBox.grid(row = 0, column = 2)
		self.bIsotopeLabel = tk.Label(self.winBetas, text = "Isotope")
		self.bIsotopeLabel.grid(row = 1, column = 0)
		self.betaLabel = tk.Label(self.winBetas, text = "Beta Energy (keV)")
		self.betaLabel.grid(row = 1, column = 1)
		self.bBranchLabel = tk.Label(self.winBetas, text = "Branching Ratio")
		self.bBranchLabel.grid(row = 1, column = 2)
		self.betaRows = [] # Will eventually be filled with UI widgets, in addBetaRow
		self.canvasBetas['width'] = self.canvasBetas.bbox(self.winBetasID)[2]
		self.canvasBetas['scrollregion'] = self.canvasBetas.bbox(self.winBetasID)
		self.panelBetas.rowconfigure(0, weight = 1)
		self.panelBetas.columnconfigure(0, weight = 1)

	def switchPanelSetup(self):
		# Hide any other panel that's visible, then show the setup panel
		self.panelDose.grid_forget()
		self.panelActivity.grid_forget()
		self.panelGammas.grid_forget()
		self.panelBetas.grid_forget()
		self.panelSetup.grid(row=1, column=0)

	def switchPanelDose(self):
		# Run the calculations before showing the results
		self.constructMaterial()
		self.bombardMaterial()
		# Hide any other panel that's visible, then show the dose panel
		self.panelSetup.grid_forget()
		self.panelActivity.grid_forget()
		self.panelGammas.grid_forget()
		self.panelBetas.grid_forget()
		# In order to minimize glitches in the scrolling, we destroy and recreate the scrollbars every time we switch panels instead of just hiding and re-showing them.
		# Yes, this is magic. It also works.
		# It does mean we need to re-setup the scrolling each time, though. That happens here.
		self.canvasDose.grid_forget()
		self.dScrollY.grid_forget()
		self.dScrollX.grid_forget()
		self.panelDose.grid(row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
		self.canvasDose = tk.Canvas(self.panelDose)
		self.canvasDose.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.dScrollY = tk.Scrollbar(self.panelDose, orient=tk.VERTICAL, command=self.canvasDose.yview)
		self.dScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.dScrollX = tk.Scrollbar(self.panelDose, orient=tk.HORIZONTAL, command=self.canvasDose.xview)
		self.dScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.winDoseID = self.canvasDose.create_window(0, 0, anchor = tk.NW, window = self.winDose)
		self.winDose.update_idletasks()
		self.canvasDose['width'] = self.canvasDose.bbox(self.winDoseID)[2]
		self.canvasDose['scrollregion'] = self.canvasDose.bbox(self.winDoseID)
		self.canvasDose['xscrollcommand'] = self.dScrollX.set
		self.canvasDose['yscrollcommand'] = self.dScrollY.set
		self.dScrollY['command'] = self.canvasDose.yview
		self.canvasDose.yview_moveto(0) # Scroll back to the top, in case we're anywhere else

	def switchPanelActivityBq(self):
		self.bq = True # Set a flag for bombardMaterial to check
		self.switchPanelActivity() # But otherwise all the work is the same

	def switchPanelActivityCi(self):
		self.bq = False # Set a flag for bombardMaterial to check
		self.switchPanelActivity() # But otherwise all the work is the same

	def switchPanelActivity(self):
		# See switchPanelDose for an explanation of the separate pieces of this.
		self.constructMaterial()
		self.bombardMaterial()
		self.panelSetup.grid_forget()
		self.panelDose.grid_forget()
		self.panelGammas.grid_forget()
		self.panelBetas.grid_forget()
		self.canvasActivity.grid_forget()
		self.aScrollY.grid_forget()
		self.aScrollX.grid_forget()
		self.panelActivity.grid(row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
		self.canvasActivity = tk.Canvas(self.panelActivity)
		self.canvasActivity.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.aScrollY = tk.Scrollbar(self.panelActivity, orient=tk.VERTICAL, command=self.canvasActivity.yview)
		self.aScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.aScrollX = tk.Scrollbar(self.panelActivity, orient=tk.HORIZONTAL, command=self.canvasActivity.xview)
		self.aScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasActivity['xscrollcommand'] = self.aScrollX.set
		self.canvasActivity['yscrollcommand'] = self.aScrollY.set
		self.winActivityID = self.canvasActivity.create_window(0, 0, anchor = tk.NW, window = self.winActivity)
		self.winActivity.update_idletasks()
		self.canvasActivity['width'] = self.canvasActivity.bbox(self.winActivityID)[2]
		self.canvasActivity['scrollregion'] = self.canvasActivity.bbox(self.winActivityID)
		self.aScrollY['command'] = self.canvasActivity.yview
		self.canvasActivity.yview_moveto(0)
	
	def switchPanelGammas(self):
		# See switchPanelDose for an explanation of the separate pieces of this.
		self.constructMaterial()
		self.bombardMaterial()
		self.panelSetup.grid_forget()
		self.panelDose.grid_forget()
		self.panelGammas.grid_forget()
		self.panelBetas.grid_forget()
		self.canvasGammas.grid_forget()
		self.gScrollY.grid_forget()
		self.gScrollX.grid_forget()
		self.panelGammas.grid(row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
		self.canvasGammas = tk.Canvas(self.panelGammas)
		self.canvasGammas.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.gScrollY = tk.Scrollbar(self.panelGammas, orient=tk.VERTICAL, command=self.canvasGammas.yview)
		self.gScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.gScrollX = tk.Scrollbar(self.panelGammas, orient=tk.HORIZONTAL, command=self.canvasGammas.xview)
		self.gScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasGammas['xscrollcommand'] = self.gScrollX.set
		self.canvasGammas['yscrollcommand'] = self.gScrollY.set
		self.winGammasID = self.canvasGammas.create_window(0, 0, anchor = tk.NW, window = self.winGammas)
		self.winGammas.update_idletasks()
		self.canvasGammas['width'] = self.canvasGammas.bbox(self.winGammasID)[2]
		self.canvasGammas['scrollregion'] = self.canvasGammas.bbox(self.winGammasID)

	def switchPanelBetas(self):
		# See switchPanelDose for an explanation of the separate pieces of this.
		self.constructMaterial()
		self.bombardMaterial()
		self.panelSetup.grid_forget()
		self.panelDose.grid_forget()
		self.panelGammas.grid_forget()
		self.panelBetas.grid_forget()
		self.canvasBetas.grid_forget()
		self.bScrollY.grid_forget()
		self.bScrollX.grid_forget()
		self.panelBetas.grid(row=1, column=0, sticky=tk.N+tk.S+tk.E+tk.W)
		self.canvasBetas = tk.Canvas(self.panelBetas)
		self.canvasBetas.grid(row = 0, column = 0, sticky = tk.N + tk.S+tk.E+tk.W)
		self.bScrollY = tk.Scrollbar(self.panelBetas, orient=tk.VERTICAL, command=self.canvasBetas.yview)
		self.bScrollY.grid(row=0, column=1, sticky=tk.N+tk.S)

		self.bScrollX = tk.Scrollbar(self.panelBetas, orient=tk.HORIZONTAL, command=self.canvasBetas.xview)
		self.bScrollX.grid(row=1, column=0, sticky=tk.E+tk.W)

		self.canvasBetas['xscrollcommand'] = self.bScrollX.set
		self.canvasBetas['yscrollcommand'] = self.bScrollY.set
		self.winBetasID = self.canvasBetas.create_window(0, 0, anchor = tk.NW, window = self.winBetas)
		self.winBetas.update_idletasks()
		self.canvasBetas['width'] = self.canvasBetas.bbox(self.winBetasID)[2]
		self.canvasBetas['scrollregion'] = self.canvasBetas.bbox(self.winBetasID)

	def addElementRow(self):
		# Create a new row on the Setup tab
		rowNum = len(self.elementRows) + 1 # One extra row for the headers.
		newNameVar = tk.StringVar()
		newRatioVar = tk.StringVar()
		newNameBox = tk.Entry(self.elementTable, textvariable = newNameVar)
		newNameBox.grid(row = rowNum, column = 0)
		newRatioBox = tk.Entry(self.elementTable, textvariable = newRatioVar)
		newRatioBox.grid(row = rowNum, column = 1)
		self.elementRows.append({"nameVar": newNameVar, "ratioVar": newRatioVar, "nameBox": newNameBox, "ratioBox": newRatioBox}) # Save all the control-variables and UI objects in our data structure

	def addGammaRow(self):
		# Create a new row on the Gammas tab
		rowNum = len(self.gammaRows) + 2 # One extra row for the headers, one more for threshold.
		newNameVar = tk.StringVar()
		newEnergyVar = tk.StringVar()
		newRatioVar = tk.StringVar()
		newNameLabel = tk.Label(self.winGammas, textvariable = newNameVar)
		newNameLabel.grid(row = rowNum, column = 0)
		newEnergyLabel = tk.Label(self.winGammas, textvariable = newEnergyVar)
		newEnergyLabel.grid(row = rowNum, column = 1)
		newRatioLabel = tk.Label(self.winGammas, textvariable = newRatioVar)
		newRatioLabel.grid(row = rowNum, column = 2)
		self.gammaRows.append({"nameVar": newNameVar, "energyVar": newEnergyVar, "ratioVar": newRatioVar, "nameLabel": newNameLabel, "energyLabel": newEnergyLabel, "ratioLabel": newRatioLabel}) # Save all the control-variables and UI objects in our data structure

	def addBetaRow(self):
		# Create a new row on the Betas tab
		rowNum = len(self.betaRows) + 2 # One extra row for the headers, one more for threshold.
		newNameVar = tk.StringVar()
		newEnergyVar = tk.StringVar()
		newRatioVar = tk.StringVar()
		newNameLabel = tk.Label(self.winBetas, textvariable = newNameVar)
		newNameLabel.grid(row = rowNum, column = 0)
		newEnergyLabel = tk.Label(self.winBetas, textvariable = newEnergyVar)
		newEnergyLabel.grid(row = rowNum, column = 1)
		newRatioLabel = tk.Label(self.winBetas, textvariable = newRatioVar)
		newRatioLabel.grid(row = rowNum, column = 2)
		self.betaRows.append({"nameVar": newNameVar, "energyVar": newEnergyVar, "ratioVar": newRatioVar, "nameLabel": newNameLabel, "energyLabel": newEnergyLabel, "ratioLabel": newRatioLabel}) # Save all the control-variables and UI objects in our data structure

	def addProductRow(self):
		# Create a new row on the Dose and Activity tabs - these are always one-to-one
		rowNum = len(self.productRows) + 1 # One extra row for the headers.
		newNameVar = tk.StringVar()
		newDoseVarG = tk.StringVar()
		newDoseVarB = tk.StringVar()
		newActivityVar = tk.StringVar()
		newDoseVarABG = tk.StringVar()
		newDoseVarABB = tk.StringVar()
		newActivityVarAB = tk.StringVar()
		newNameLabelD = tk.Label(self.winDose, textvariable = newNameVar)
		newNameLabelD.grid(row = rowNum, column = 0)
		newNameLabelA = tk.Label(self.winActivity, textvariable = newNameVar)
		newNameLabelA.grid(row = rowNum, column = 0)
		newDoseLabelG = tk.Label(self.winDose, textvariable = newDoseVarG)
		newDoseLabelG.grid(row = rowNum, column = 1)
		newDoseLabelB = tk.Label(self.winDose, textvariable = newDoseVarB)
		newDoseLabelB.grid(row = rowNum, column = 2)
		newDoseLabelABG = tk.Label(self.winDose, textvariable = newDoseVarABG)
		newDoseLabelABG.grid(row = rowNum, column = 3)
		newDoseLabelABB = tk.Label(self.winDose, textvariable = newDoseVarABB)
		newDoseLabelABB.grid(row = rowNum, column = 4)
		newActivityLabel = tk.Label(self.winActivity, textvariable = newActivityVar)
		newActivityLabel.grid(row = rowNum, column = 1)
		newActivityLabelAB = tk.Label(self.winActivity, textvariable = newActivityVarAB)
		newActivityLabelAB.grid(row = rowNum, column = 2)
		 # Save all the control-variables and UI objects in our data structure
		self.productRows.append({"nameVar": newNameVar, "doseVarG": newDoseVarG, "doseVarB": newDoseVarB, "activityVar": newActivityVar, "doseVarABG": newDoseVarABG, "doseVarABB": newDoseVarABB, "activityVarAB": newActivityVarAB, "nameLabelA": newNameLabelA, "nameLabelD": newNameLabelD, "doseLabelB": newDoseLabelB, "doseLabelG": newDoseLabelG, "activityLabel": newActivityLabel, "doseLabelABG": newDoseLabelABG, "doseLabelABB": newDoseLabelABB, "activityLabelAB": newActivityLabelAB})
	
	def destroyGammaRows(self):
		# Empty the Gammas table so that we can fill it with new data
		for row in self.gammaRows:
			row["nameLabel"].grid_forget()
			row["energyLabel"].grid_forget()
			row["ratioLabel"].grid_forget()
		self.gammaRows = []
	
	def destroyBetaRows(self):
		# Empty the Gammas table so that we can fill it with new data
		for row in self.betaRows:
			row["nameLabel"].grid_forget()
			row["energyLabel"].grid_forget()
			row["ratioLabel"].grid_forget()
		self.betaRows = []
	
	def destroyProductRows(self):
		# Empty the Dose/Activity table so we can refill it
		for row in self.productRows:
			row["nameLabelA"].grid_forget()
			row["nameLabelD"].grid_forget()
			row["doseLabelB"].grid_forget()
			row["doseLabelG"].grid_forget()
			row["activityLabel"].grid_forget()
			row["doseLabelABB"].grid_forget()
			row["doseLabelABG"].grid_forget()
			row["activityLabelAB"].grid_forget()
		self.productRows = []
	
	def locateFluxProfile(self, event):
		# Ask the user for a flux profile file
		self.profileVar.set(tkFileDialog.askopenfilename(title="Select Flux Profile") or self.profileVar.get())
		path = self.profileVar.get()
		if path: # Check to see if they gave us one
			reader = csv.reader(open(path)) # And if they did, load it in
			iFlux = [(float(r[0]), float(r[1])) for r in reader]
			tFlux = np.transpose(iFlux)
			edsSrc = EAFDataSource()._src_group_struct # Get the EAF group structure
			self.flux = pointwise_collapse(edsSrc, np.flipud(tFlux[0]), np.flipud(tFlux[1] * 1.738e16 / 230)) # Scale the flux from flux per source neutron to flux at 1 kW, then interpolate to fit EAF group structure

	def constructMaterial(self):
		# Take all the isotopes mentioned in the Setup tab, combine them into a PyNE material
		ratioType = self.ratioTypeVar.get()
		isotopes = {}
		for row in self.elementRows:
			eltName = row["nameVar"].get()
			ratio = row["ratioVar"].get()
			if eltName and ratio:
				isotopes[eltName] = float(ratio)
		if ratioType == 'Mass Ratio':
			self.material = Material(isotopes, mass=float(self.massVar.get()))
		else:
			self.material = Material(mass=float(self.massVar.get()))
			self.material.from_atom_frac(isotopes) # Automatically switches from atom ratios to mass ratios
		# Manually replace "Natural Tantalum" with correct natural distribution of isotopes. PyNE incorrectly lists natural Tantalum as 0.012% Ta-180 and 99.988% Ta-181, when in actuality it is 0.012% Ta-180M and 99.988% Ta-181.
		if 730000000 in self.material:
			self.material[731800001] = self.material[730000000] * 0.00011943600030691943
			self.material[731810000] = self.material[730000000] * 0.999880563999693
			del self.material[730000000]
		self.material = self.material.expand_elements() # Replaces elements with the natural distribution of isotopes; this will fail if you ask for "Natural Plutonium" or similar. Don't try to irradiate natural Plutonium. It doesn't exist.

	def bombardMaterial(self):
		# This is where everything happens.
		t = Transmuter()
		reader = csv.reader(open("air_gamma.csv")) # This file is from NIST: http://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/air.html
		air_gamma = np.transpose([[float(x) for x in row] for row in reader])
		gammaf = interp1d(air_gamma[0], air_gamma[1]) # Interpolate mu/rho data from NIST. This could be upgraded to a cubic interpolation for a slight improvement in accuracy.
		cal = pdt.Calendar()
		deltaT = (cal.parseDT(self.timeVar.get(), sourceTime=datetime.datetime.min)[0] - datetime.datetime.min).total_seconds() # Parse the irradiation time
		self.product = t.transmute(self.material, float(deltaT), self.flux * float(self.powerVar.get())) # Get PyNE to do the transmutation for us.
		for iso in self.product:			# These three lines fix a bug involving the irradiation of W-186.
			if np.isnan(decay_const(iso)):	# PyNE claims it produces a negligible amount of Ta-187, and the half-life of Ta-187 is unknown.
				del self.product[iso]		# This removes all isotopes with unknown half-lives from the output.
		if self.delayVar.get():				# If we don't have a Time After Bombardment, don't calculate dose after decaying
			decayT = (cal.parseDT(self.delayVar.get(), sourceTime=datetime.datetime.min)[0] - datetime.datetime.min).total_seconds() # Parse decay time
			self.product_after = t.transmute(self.product, decayT, 0) # PyNE's decay() function is broken, so we just irradiate with 0 flux, which is equivalent to allowing it to decay.
		else:
			self.product_after = {}
		self.destroyProductRows() # Wipe the tables, fresh start.
		self.destroyGammaRows()
		self.destroyBetaRows()
		totalDoseG = 0 # Set up accumulators...
		totalDoseABG = 0
		totalDoseB = 0 # Set up accumulators...
		totalDoseABB = 0
		totalAct = 0
		totalActAB = 0
		self.addProductRow() # ... to put in a row at the top...
		self.productRows[0]["nameVar"].set("TOTAL") # ... with the total dose and activity.
		for iso, mass in sorted(self.product.mult_by_mass().items(), key=lambda x: -x[1]*decay_const(x[0])): # Sort isotopes by the activity in the initial product.
			if decay_const(iso) == 0.0: # If they're stable, don't show them.
				continue
			self.addProductRow() # Create a new table row
			self.productRows[-1]["nameVar"].set(nucname.name(iso))
			act = mass * decay_const(iso) * 6.022e23 / atomic_mass(iso) # Convert from mass to number, then to activity.
			if self.bq: # Check if we want output in Becquerels or Curies
				self.productRows[-1]["activityVar"].set(str(act))
			else:
				self.productRows[-1]["activityVar"].set(str(act/37000000)) # Bq/mCi conversion
			if iso in self.product_after: # If there's any left after allowing it to decay...
				actAB = self.product_after.mult_by_mass()[iso] * decay_const(iso) * 6.022e23 / atomic_mass(iso) # ... then note down the activity there.
				if self.bq:
					self.productRows[-1]["activityVarAB"].set(str(actAB))
				else:
					self.productRows[-1]["activityVarAB"].set(str(actAB/37000000)) # Bq/mCi conversion
			else: # Otherwise, leave it at 0.
				actAB = 0
				self.productRows[-1]["activityVarAB"].set("0")
			doseG = 0 # Accumulators to sum the dose over all the gammas
			doseABG = 0
			doseB = 0 # Accumulators to sum the dose over all the betas
			doseABB = 0
			gammas = np.array(gamma_photon_intensity(iso)) * np.array(gamma_energy(iso)) / 100
			for idx in range(len(gamma_photon_intensity(iso))):
				if not (np.isnan(gamma_energy(iso)[idx][0]) or np.isnan(gamma_photon_intensity(iso)[idx][0])): # Ignore gammas with unknown energy or branch-ratio
					if self.thresholdVar.get() and gamma_photon_intensity(iso)[idx][0] >= float(self.thresholdVar.get()): # If below threshold energy, don't put in the table, but still use in dose calculation
						self.addGammaRow()
						self.gammaRows[-1]["nameVar"].set(nucname.name(iso))
						self.gammaRows[-1]["energyVar"].set(gamma_energy(iso)[idx][0])
						self.gammaRows[-1]["ratioVar"].set(gamma_photon_intensity(iso)[idx][0])

					mev = gamma_energy(iso)[idx][0] / 1000 # Default energy is specified in keV. Convert.
					gf = gammaf(mev) # Get interpolated mu/rho for that energy of gammas in air
					dpa = gamma_photon_intensity(iso)[idx][0] * 5.263e-6 * mev * gf / 90000 # Get the dose per Becquerel
					doseG += dpa * act # And then the actual dose (in R/hr)
					doseABG += dpa * actAB # So we can update our accumulators accordingly
			for idx in range(len(beta_intensity(iso))): # Same as above, for betas
				if not np.isnan(beta_intensity(iso)[idx]):
					if self.thresholdVar.get() and beta_intensity(iso)[idx] >= float(self.thresholdVar.get()):
						self.addBetaRow()
						self.betaRows[-1]["nameVar"].set(nucname.name(iso))
						self.betaRows[-1]["energyVar"].set(beta_average_energy(iso)[idx])
						self.betaRows[-1]["ratioVar"].set(beta_intensity(iso)[idx])

					dpa = 8e-12 * 100 * beta_intensity(iso)[idx] / (0.3 * 0.3) # Approximate formula for beta dose per Becquerel from the Handbook of Health Physics and Radiological Health - yes, this does not depend on beta energy. An improvement that could be made here is to find a better formula, or a data table like the one we use for gammas, and take into account the beta energy.
					doseB += dpa * act
					doseABB = dpa * actAB
			self.productRows[-1]["doseVarB"].set(str(doseB * 1000)) # 1 R/hr = 1000 mR/hr
			self.productRows[-1]["doseVarABB"].set(str(doseABB * 1000))
			self.productRows[-1]["doseVarG"].set(str(doseG * 1000)) # 1 R/hr = 1000 mR/hr
			self.productRows[-1]["doseVarABG"].set(str(doseABG * 1000))
			totalDoseB += doseB # Update our accumulators
			totalDoseG += doseG # Update our accumulators
			totalDoseABB += doseABB
			totalDoseABG += doseABG
			totalAct += act
			totalActAB += actAB
		# These are all for the TOTAL row
		if self.bq:
			self.productRows[0]["activityVar"].set(str(totalAct))
			self.productRows[0]["activityVarAB"].set(str(totalActAB))
		else:
			self.productRows[0]["activityVar"].set(str(totalAct/37000000)) # Bq/mCi conversion
			self.productRows[0]["activityVarAB"].set(str(totalActAB/37000000))
		self.productRows[0]["doseVarB"].set(str(totalDoseB * 1000)) # 1 R/hr = 1000 mR/hr
		self.productRows[0]["doseVarABB"].set(str(totalDoseABB * 1000))
		self.productRows[0]["doseVarG"].set(str(totalDoseG * 1000)) # 1 R/hr = 1000 mR/hr
		self.productRows[0]["doseVarABG"].set(str(totalDoseABG * 1000))



app = IRApplication() # Create an instance of the application object defined above
app.master.title = "Irradiation Planning Tool" # Name it
app.mainloop() # And run until someone hits Quit