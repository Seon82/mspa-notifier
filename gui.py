from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QPixmap, QMouseEvent, QIcon, QPalette, QMovie, QColor, QCursor
from PyQt5.QtMultimedia import QSoundEffect
import webbrowser
import pickle
import os
from random import choice as randchoice
from core import *


class QDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        pass

class Notifier():
    ''' Manages the active notification and the notification queue.
    - volume is a float between 0 and 1 that manages the notification volume.'''
    def __init__(self, volume = 1):
        self.volume = volume
        self.activeNotification = None
        self.queue = []

    def push(self, notification):
        '''Adds a notification to the queue. Does nothing if a notification with the same name is already present in the queue.'''
        if self.activeNotification == None:
            self.activeNotification = notification
            notification.display(self.volume)
        else: # Tries to add to queue
            notInQueue = True
            for waitingNotification in self.queue:
                if notification.name == waitingNotification.name:
                    notInQueue = False
                    break
            if notInQueue:
                self.queue.append(notification)

    def update(self):
        '''Call after killing the active notification. Processes the queue.'''
        if self.queue == []:
            self.activeNotification = None
        else:
            self.activeNotification = self.queue.pop(0)
            self.activeNotification.display(self.volume)


class Notification(QMainWindow):
    '''Transparent window containing an image or animated gif, used to display notifications.'''

    def __init__(self, name, notifier, artPath, link, sound=None, *args, **kwargs):
        '''- name : a string
        - notifier : a Notifier object used to manage this notification
        - artPath : a string containing the path to the image file to be displayed
        - link : a string containing the link to be opened when left-clicking the notification
        - sound : a string containing the path to the object or None. Set to None for silent notifiations.'''
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.name = name
        self.notifier = notifier
        self.link = link
        self.artPath = artPath
        self.isMovie = self.artPath.endswith(".gif")
        if sound == None:
            self.sound = None
        else:
            self.sound = QSoundEffect()
            self.sound.setSource(QUrl.fromLocalFile(sound))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        imageLabel = QLabel()
        self.setCentralWidget(imageLabel)
        if self.isMovie:
            self.art = QMovie(self.artPath)
            self.art.jumpToNextFrame()
            imageLabel.setMovie(self.art)
            self.moveToBottomRight(self.art.frameRect().width(), self.art.frameRect().height())
        else:
            self.art = QPixmap(self.artPath)
            imageLabel.setPixmap(self.art)
            self.moveToBottomRight(self.art.width(), self.art.height())

    def moveToBottomRight(self, x, y):
        '''Moves the notification window to the bottom-right of the screen, above the taskbar'''
        screen =  QDesktopWidget().availableGeometry()
        x_pos = screen.width() - x
        y_pos = screen.height() - y
        self.move(x_pos, y_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.close()
            webbrowser.open_new_tab(self.link)
        elif event.button() == Qt.RightButton:
            self.close()


    def display(self, volume = 1):
        '''Show the notification window and plays the sound.'''
        super().show()
        if self.isMovie:
            self.art.start()
        if self.sound:
            self.sound.setVolume(volume)
            self.sound.play()

    def close(self):
        '''Updates notifier and closes window'''
        super().close()
        self.notifier.update()

class Feed():
    '''A generic feed object, used to track updates from a remote source'''
    def __init__(self, name, link, imageFolder, notifier, active = True, updateFreq = 5, psInactive = False, psUpdateFreq = 30, sound = None, latestLink = ''):
        '''- name : a string
        - link : a string containing the tracked remote source
        - imageFolder : a string containing a path to the directory containing the art to be used for the notifications
        - notifier : a Notifier object
        - active : a bool, describing the feed is active (periodically monitoring remote source)
        - updateFreq : a float, describing how often the remote source should be checked. Useless if active is set to False.
        - psInactive : a bool, describing whether the feed should become inactive when the battery dips below 20%
        - psUdpdateFreq : a float, describing how often the remote source should be checked when battery is under 20%. Useless if psInactive is set to True.
        - sound : a string containing the path to the sound file to be played in notifications
        - latestLink : a string, containing a link to the latest webpage given by the remote source'''
        self.name = name
        self.link = link
        self.imageFolder = imageFolder
        self.active = active
        self.updateFreq = updateFreq
        self.psInactive = psInactive
        self.psUpdateFreq = psUpdateFreq
        self.sound = sound
        self.latestLink = latestLink
        self.reset(notifier)

    def reset(self, notifier):
        '''Adds the notifier and starts timer. Use when loading Feed from memory'''
        self.notifier = notifier
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetchUpdate)
        if self.isActive():
            self.fetchUpdate()
            self.timer.start(self.getUpdateFreq())

    def isActive(self):
        ''' Returns True iif the feed should be updating'''
        return self.active or (not self.psInactive and isSavingPower())

    def getUpdateFreq(self):
        ''' Returns the update frequency of the feed. Beware, does not check whether the feed is active.'''
        if isSavingPower():
            return self.psUpdateFreq*60000 # to milliseconds
        return self.updateFreq*60000 # to milliseconds

    def generateNotification(self):
        '''Returns a notification made with a random image'''
        try:
            imageExtensions = [".bmp", ".jpg", ".png", ".pbm", ".gif", ".ppm", ".xbm", ".xpm", "jpeg"]
            images = [file for file in os.listdir(self.imageFolder) if file[-4:] in imageExtensions]
            imageFile = randchoice(images)
            imagePath = os.path.join(self.imageFolder, imageFile)
        except:
            print("Image file not found, defaulting to fallback.")
            imagePath = "media/system/fallback.png"

        return Notification(self.name, self.notifier, imagePath, self.latestLink, self.sound)

    def updateParams(self, active, updateFreq, psInactive, psUpdateFreq, imageFolder, sound):
        '''Used to update the feed's parameters. Resets the feed's timer.'''
        self.active = active
        self.updateFreq = updateFreq
        self.psInactive = psInactive
        self.psUpdateFreq = psUpdateFreq
        self.imageFolder = imageFolder
        self.sound = sound
        if self.isActive():
            self.timer.start(self.getUpdateFreq())
        else:
            self.timer.stop()
        self.save()

    def save(self):
        '''Saves the feed to memory using pickle under ./data/feeds/self.name
        The QTimer and Notifier object aren't saved and must be restored using self.reset(notifier) after loading'''
        timer = self.timer
        notifier = self.notifier
        self.timer = None
        self.notifier = None
        with open("data/feeds/" + self.name, 'wb') as f:
            pickle.dump(self, f)
        self.timer = timer
        self.notifier = notifier


class RSSFeed(Feed):
    '''Inherits the Feed generic class. Use for an RSS feed source'''
    def fetchUpdate(self, force = False):
        '''Fetches update from the remote source.
        Also saves the Feed and pushes the update to the notifier in case an update was found.
        force = True pushes a notification to the notifier even if there was no update'''
        try:
            link = getLatestRSS(self.link)
        except:
            print("Couldn't connect to website")
            pass
        if link!=self.latestLink:
            self.latestLink = link
            self.notifier.push(self.generateNotification())
            self.save()
        elif force:
            self.notifier.push(self.generateNotification())


class WebsiteFeed(Feed):
    '''Inherits the Feed generic class. Use to monitor a link with a fixed xpath from any website'''
    def __init__(self, xpath, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xpath = xpath

    def fetchUpdate(self, force = False):
        '''Fetches update from the remote source.
        Also saves the Feed and pushes the update to the notifier in case an update was found.
        force = True pushes a notification to the notifier even if there was no update'''
        try:
            link = getLatestLink(self.link, self.xpath)
        except:
            print("Couldn't connect to website")
            pass
        if link!=self.latestLink:
            self.latestLink = link
            self.notifier.push(self.generateNotification())
            self.save()
        elif force:
            self.notifier.push(self.generateNotification())

class SettingsWindow(QMainWindow):
    '''A window containing the settings for each feed, as well as global settings'''
    def __init__(self, tray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tray = tray
        self.volume = self.tray.notifier.volume * 100
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon('media/system/settings.png'))
        self.sections = []

        widget = QWidget()
        mainLayout = QVBoxLayout(widget)

        scroll =QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.setCentralWidget(scroll)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Add a section by feed
        for feed in self.tray.feeds:
            section = SettingsSection(feed)
            mainLayout.addWidget(section)
            self.sections.append(section)

        # Volume control
        volumeGroup = QGroupBox("Notification volume")
        mainLayout.addWidget(volumeGroup)
        vBox = QVBoxLayout(volumeGroup)
        self.volumeSlider = QSlider(Qt.Horizontal)
        vBox.addWidget(self.volumeSlider)
        self.volumeSlider.setValue(self.volume)
        self.volumeSlider.valueChanged.connect(self.updateVolume)

        # Save button
        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.save)
        mainLayout.addWidget(saveButton)

        # Resize window to fit scrollbar
        self.resize(self.sizeHint().width()*1.05,self.sizeHint().height()*1.7)

    def updateVolume(self):
        self.volume = self.volumeSlider.value()

    def save(self):
        '''Updates all modified feeds with the changes'''
        for section in self.sections:
            section.updateFeed()
        self.tray.updateVolume(self.volume)
        self.close()

class SettingsSection(QGroupBox):
    '''A widget containing the settings for an individual feed'''
    def __init__(self, feed, *args, **kwargs):
        '''feed is a RSSFeed or a WebsiteFeed'''
        super().__init__(*args, **kwargs)
        self.feed = feed
        self.setTitle(self.feed.name)
        grid = QGridLayout(self)

        # Create top widgets
        grid.addWidget(QLabel("Notifications active"))
        self.active = QCheckBox()
        self.active.setChecked(self.feed.active)
        self.active.stateChanged.connect(self.updateDisplay)
        grid.addWidget(self.active, 0,1)
        textUpdate = QLabel("Check for updates every")
        grid.addWidget(textUpdate)
        self.updateFreq = QDoubleSpinBox()
        self.updateFreq.setDecimals(0)
        self.updateFreq.setMinimum(1)
        self.updateFreq.setValue(self.feed.updateFreq)
        grid.addWidget(self.updateFreq, 1,1)
        textMinutes = QLabel("minutes")
        grid.addWidget(textMinutes, 1, 2)

        # Create power saving mode group box
        palette = QPalette()
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QApplication.palette().color(QPalette.Disabled, QPalette.WindowText))
        psGroup = QGroupBox("When battery is low")
        psGroup.setPalette(palette)
        grid.addWidget(psGroup, 2,0,2,0)
        psGrid = QGridLayout(psGroup)
        psGrid.addWidget(QLabel("Stop updating"),0,0)
        self.psInactive = QCheckBox()
        self.psInactive.setChecked(self.feed.psInactive)
        self.psInactive.stateChanged.connect(self.updateDisplay)
        psGrid.addWidget(self.psInactive, 0,1)
        psTextUpdate = QLabel("Update every")
        psGrid.addWidget(psTextUpdate,1,0)
        self.psUpdateFreq = QDoubleSpinBox()
        self.psUpdateFreq.setDecimals(0)
        self.psUpdateFreq.setMinimum(1)
        self.psUpdateFreq.setValue(self.feed.psUpdateFreq)
        psGrid.addWidget(self.psUpdateFreq, 1, 1)
        psMinutesText = QLabel("minutes")
        psGrid.addWidget(psMinutesText, 1, 2)

        # Add macro and sound file selection
        macroSelection = QPushButton("Macro folder")
        self.macroText = QLabel("..."+os.path.abspath(feed.imageFolder)[-15:])
        self.macroText.setToolTip(os.path.abspath(feed.imageFolder))
        macroSelection.clicked.connect(lambda _: self.selectMacroDir())
        soundSelection = QPushButton("Notification sound")
        self.soundText = QLabel("..."+os.path.abspath(feed.sound)[-15:])
        self.soundText.setToolTip(os.path.abspath(feed.sound))
        soundSelection.clicked.connect(lambda _: self.selectSoundFile())

        grid.addWidget(macroSelection, 5,0)
        grid.addWidget(self.macroText, 5,1)
        grid.addWidget(soundSelection, 6,0)
        grid.addWidget(self.soundText, 6,1)
        # Groups you can disable depending on checkbox values
        self.hideable = [psGroup, textUpdate, self.updateFreq, textMinutes]
        self.psHideable = [psTextUpdate, self.psUpdateFreq, psMinutesText]

        # Update
        self.updateDisplay()


    def selectMacroDir(self):
        dialog = QFileDialog()
        name = dialog.getExistingDirectory(caption = "Choose macro directory", directory = "media", options = QFileDialog.ShowDirsOnly)
        if name!='':
            self.macroText.setText("..."+os.path.abspath(name)[-15:])
            self.macroText.setToolTip(name)

    def selectSoundFile(self):
        dialog = QFileDialog()
        name, _ = dialog.getOpenFileName(caption = "Choose notification sound", directory = "media", filter = "Sound files (*.wav)")
        if name!='':
            self.soundText.setText("..."+os.path.abspath(name)[-15:])
            self.soundText.setToolTip(name)


    def updateDisplay(self):
        if self.psInactive.isChecked():
            for widget in self.psHideable:
                widget.setEnabled(False)
        else:
            for widget in self.psHideable:
                widget.setEnabled(True)

        if self.active.isChecked():
            for widget in self.hideable:
                widget.setEnabled(True)
        else:
            for widget in self.hideable:
                widget.setEnabled(False)

    def updateFeed(self):
        '''If values were changed, updates the feed's seetings'''
        active, updateFreq = self.active.isChecked(), self.updateFreq.value()
        psInactive, psUpdateFreq = self.psInactive.isChecked(), self.psUpdateFreq.value()
        imageFolder, sound = self.macroText.toolTip(), self.soundText.toolTip()
        imageFolder, sound = os.path.relpath(imageFolder), os.path.relpath(sound)
        if active != self.feed.active or updateFreq != self.feed.updateFreq\
        or psInactive != self.feed.psInactive or psUpdateFreq != self.feed.psUpdateFreq\
        or imageFolder != self.feed.imageFolder or sound != self.feed.sound:
            self.feed.updateParams(active, updateFreq, psInactive, psUpdateFreq, imageFolder, sound)

class TrayApp(QSystemTrayIcon):
    '''The main tray window'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feeds = []
        volume = self.loadVolume()
        self.notifier = Notifier(volume/100)
        self.loadFeeds("data/feeds/")
        self.settingsWindow = SettingsWindow(self)

        # Create the icon
        icon = QIcon("media/system/icon.png")
        self.setIcon(icon)
        self.setVisible(True)

        self.setToolTip("MSPA Notifier")

        # Create the menu
        menu = QMenu()
        updateAction = menu.addAction("Update NOW")
        updateAction.triggered.connect(self.updateAll)
        fakeMenu = menu.addMenu("Fake update")
        for feed in self.feeds:
            forceUpdate = fakeMenu.addAction(feed.name)
            forceUpdate.triggered.connect(lambda _, feed=feed:feed.fetchUpdate(force=True))
        settingsAction = menu.addAction("Settings")
        settingsAction.triggered.connect(self.openSettingsWindow)
        quitAction = menu.addAction("Quit")
        quitAction.triggered.connect(app.exit)

        # Add the menu to the tray
        self.setContextMenu(menu)

    def updateAll(self):
        '''Forces all active feeds to check for updates'''
        for feed in self.feeds:
            if feed.isActive():
                feed.fetchUpdate()

    def openSettingsWindow(self):
        '''Opens the settings window'''
        self.settingsWindow.show()

    def addFeed(self, feed):
        '''Adds a feed to the self.feed attribute list.'''
        self.feeds.append(feed)

    def loadFeeds(self, path):
        '''Loads the feeds in the directory indicated by path from memory.
        path must contain nothing but memory file created by Feed.save'''
        for file in os.listdir(path):
            file = os.path.join(path, file)
            with open(file, 'rb') as f:
                feed = pickle.load(f)
            feed.reset(self.notifier)
            self.addFeed(feed)

    def createRssFeed(self, *args, **kwargs):
        '''Creates a new RSSFeed and adds it to the app's feeds'''
        notifier = self.notifier
        feed = RSSFeed(notifier = notifier, *args, **kwargs)
        self.addFeed(feed)

    def createWebsiteFeed(self, *args, **kwargs):
        '''Creates a new WebsiteFeed and adds it to the app's feeds'''
        notifier = self.notifier
        feed = WebsiteFeed(notifier = notifier, *args, **kwargs)
        self.addFeed(feed)

    def updateVolume(self, volume):
        '''Updates the volume attribute of the notifier and saves the new volume to memory'''
        self.notifier.volume = volume
        with open("data/volume", "w") as f:
            f.write(str(int(volume)))

    def loadVolume(self):
        '''Loads and returns the saved volume setting'''
        with open("data/volume", "r") as f:
            volume = int(f.read())
        return volume


app = QApplication([])
app.setQuitOnLastWindowClosed(False)
tray = TrayApp()
app.exec_()