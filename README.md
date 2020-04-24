# [WIP] mspa-notifier
This project intends to create a notifier for the Homestuck^2 and Vast Error webcomics. Complete with custom, noisy, startling, intrusive image notifications (who likes those boring toast notifications anyway?)\
In the long run, I want it to become a full-fledged customizable notifier, with the ability to monitor into any RSS feed and detect changes in a website's element (supplied through an xpath by the user), thus giving anyone the convenience of getting all their updates in one place in a completely free form, the images being user-supplied.
## Prerequisites
The code requires `python 3`.
Tested on Windows 10.

## Installation
Clone or download and extract the repository. 

Run `pip3 install -r requirements.txt` and you're good to go!

Run `gui.py`and the app logo should show up in your taskbar.

#### How to make the code run at boot
Press Win + R, type `shell:startup` and validate.\
A directory opens, just put a shortcut to the gui.py file inside.

## Known bugs
* All unopened notifications will be lost after shutdown.
* Will display info for the battery-saving mode in settings even on desktop computers.

Feel free to report any bug you find by opening an issue!
