from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QPixmap, QMouseEvent, QIcon, QPalette, QMovie, QColor, QCursor
from PyQt5.QtMultimedia import QSoundEffect
import webbrowser
import pickle
import os
from random import choice as randchoice
from core import *


'''
TODO :
- test current code [DONE]
- implement RSS & website parser in core.py [DONE]
- add volume control [DONE]
- add volume persistence [DONE]
- add saving and loading feeds -> 1 file per feed [DONE]
- add animated .gif support [DONE]
- run as service
'''

class Notifier():
    ''' Manages the active notification and the notification queue'''
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
        '''Call after killing the active notification.'''
        if self.queue == []:
            self.activeNotification = None
        else:
            self.activeNotification = self.queue.pop(0)
            self.activeNotification.display(self.volume)


class Notification(QMainWindow):
    '''Transparent window containing a notification. Use Notification.show to display.'''

    def __init__(self, name, notifier, artPath, link, sound=None, *args, **kwargs):
        '''Image and Sound should be paths to files. Set Sound to None for silent notifications'''
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
        screen =  QDesktopWidget().availableGeometry()
        x_pos = screen.width() - x
        y_pos = screen.height() - y
        self.move(x_pos, y_pos)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            self.close()
            webbrowser.open_new_tab(self.link)
        elif QMouseEvent.button() == Qt.RightButton:
            self.close()

    def display(self, volume = 1):
        '''Shows notification window and plays sound'''
        super().show()
        if self.isMovie:
            self.art.start()
        if self.sound:
            self.sound.setVolume(volume)
            self.sound.play()

    def close(self):
        '''Updates notifier before closing'''
        super().close()
        self.notifier.update()

class Feed():
    def __init__(self, name, link, imageFolder, notifier, active = True, updateFreq = 5, psInactive = False, psUpdateFreq = 30, sound = None, latestLink = ''):
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
        imageFile = randchoice(os.listdir(self.imageFolder))
        imagePath = os.path.join(self.imageFolder, imageFile)
        return Notification(self.name, self.notifier, imagePath, self.latestLink, self.sound)

    def updateParams(self, active, updateFreq, psInactive, psUpdateFreq):
        '''Used to update the feed's parameters. Resets the feed's timer.'''
        self.active = active
        self.updateFreq = updateFreq
        self.psInactive = psInactive
        self.psUpdateFreq = psUpdateFreq
        if self.isActive():
            self.timer.start(self.getUpdateFreq())
        else:
            self.timer.stop()
        self.save()

    def save(self):
        timer = self.timer
        notifier = self.notifier
        self.timer = None
        self.notifier = None
        with open("data/feeds/" + self.name, 'wb') as f:
            pickle.dump(self, f)
        self.timer = timer
        self.notifier = notifier


class RSSFeed(Feed):
    def fetchUpdate(self, force = False):
        '''force = True pushes a notification to the notifier even if there was no update'''
        link = getLatestRSS(self.link)
        try:
            if link!=self.latestLink:
                self.latestLink = link
                self.save()
                self.notifier.push(self.generateNotification())
            elif force:
                self.notifier.push(self.generateNotification())
        except:
            print("Couldn't connect to website")
            pass

class WebsiteFeed(Feed):
    def __init__(self, xpath, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xpath = xpath

    def fetchUpdate(self, force = False):
        '''force = True pushes a notification to the notifier even if there was no update'''
        try:
            link = getLatestLink(self.link, self.xpath)
            if link!=self.latestLink:
                self.latestLink = link
                self.save()
                self.notifier.push(self.generateNotification())
            elif force:
                self.notifier.push(self.generateNotification())
        except:
            print("Couldn't connect to website")
            pass

class SettingsWindow(QMainWindow):
    def __init__(self, tray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tray = tray
        self.volume = self.tray.notifier.volume * 100
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon('media/icons/settings.png'))
        self.sections = []

        widget = QWidget()
        self.setCentralWidget(widget)
        mainLayout = QVBoxLayout(widget)

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

    def updateVolume(self):
        self.volume = self.volumeSlider.value()

    def save(self):
        '''Updates all modified feeds with the changes'''
        for section in self.sections:
            section.updateFeed()
        self.tray.updateVolume(self.volume)
        self.close()

class SettingsSection(QGroupBox):
    def __init__(self, feed, *args, **kwargs):
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
        psGrid.addWidget(QLabel("Stop updating"),3,0)
        self.psInactive = QCheckBox()
        self.psInactive.setChecked(self.feed.psInactive)
        self.psInactive.stateChanged.connect(self.updateDisplay)
        psGrid.addWidget(self.psInactive, 3,1)
        psTextUpdate = QLabel("Update every")
        psGrid.addWidget(psTextUpdate,4,0)
        self.psUpdateFreq = QDoubleSpinBox()
        self.psUpdateFreq.setDecimals(0)
        self.psUpdateFreq.setMinimum(1)
        self.psUpdateFreq.setValue(self.feed.psUpdateFreq)
        psGrid.addWidget(self.psUpdateFreq, 4, 1)
        psMinutesText = QLabel("minutes")
        psGrid.addWidget(psMinutesText, 4, 2)

        # Groups you can disable depending on checkbox values
        self.hideable = [psGroup, textUpdate, self.updateFreq, textMinutes]
        self.psHideable = [psTextUpdate, self.psUpdateFreq, psMinutesText]

        # Update
        self.updateDisplay()

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
        if active != self.feed.active or updateFreq != self.feed.updateFreq\
        or psInactive != self.feed.psInactive or psUpdateFreq != self.feed.psUpdateFreq:
            self.feed.updateParams(active, updateFreq, psInactive, psUpdateFreq)

class TrayApp(QSystemTrayIcon):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feeds = []
        volume = self.loadVolume()
        self.notifier = Notifier(volume/100)
        self.loadFeeds("data/feeds/")
        self.settingsWindow = SettingsWindow(self)

        # Create the icon
        icon = QIcon("media/icons/icon.png")
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
        self.settingsWindow.show()

    def addFeed(self, feed):
        self.feeds.append(feed)

    def loadFeeds(self, path):
        for file in os.listdir(path):
            file = os.path.join(path, file)
            with open(file, 'rb') as f:
                feed = pickle.load(f)
            feed.reset(self.notifier)
            self.addFeed(feed)

    def createRssFeed(self, *args, **kwargs):
        notifier = self.notifier
        feed = RSSFeed(notifier = notifier, *args, **kwargs)
        self.addFeed(feed)

    def createWebsiteFeed(self, *args, **kwargs):
        notifier = self.notifier
        feed = WebsiteFeed(notifier = notifier, *args, **kwargs)
        self.addFeed(feed)

    def updateVolume(self, volume):
        self.notifier.volume = volume
        with open("data/volume", "w") as f:
            f.write(str(int(volume)))

    def loadVolume(self):
        with open("data/volume", "r") as f:
            volume = int(f.read())
        return volume

app = QApplication([])
tray = TrayApp()
app.exec_()