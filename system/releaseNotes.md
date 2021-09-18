# Version 3.037

## Improved - Theme Selection

My Account now includes a dropdown menu for theme selection. No more guessing what the theme names are

![jimi - theme changing](https://user-images.githubusercontent.com/66521110/133906387-bf9f96b8-4221-48ab-a454-623b9f0d379c.gif)

## Improved - Storage 

Added UI options for file tokens and downloading of already uploaded files

## Improved - Object Revisions

Object revision UI is no longer in BETA and now is officially released. As part of this release the UI has been updated to include the revision creator as well as a view button that enables you to see the content of the revision without restoring the object

![jimi - Revision History](https://user-images.githubusercontent.com/66521110/133906395-f97b733d-7514-4ffc-953d-d6c04b580a46.gif)

## Fixed - Worker Killed Exception Message

Added message to worker killed exception to make it clear that the failure on the status page was caused by the system killing the trigger

## Fixed - Status Page Polling

The status page polling improved to reduce network utilization

## Fixed - Cluster Checksum and Updates

Fixed a bug within the cluster checksum and update system that meant users had to update multiple times before it would be successful

## Fixed - System HealthChecker Crashing

An issue that caused the health checker service to crash has been resolved

# Version 3.036

## Features -

### Changeable User Themes 

Users now have the ability to change themes, this can be done through the My Accounts page

### Update My Account Page

Ability to change name and email address associated

![image](https://user-images.githubusercontent.com/66521110/133906668-cb097e21-11c9-4009-9e4c-5e2273d8fb3e.png)

### Add Whats New

Whats New ( This ) panel has been added to inform users of changes after an upgrade has taken place. Once a user pressing the "Close" button the panel will not be visible until the next upgrade

## Bug Fixes -

### Enabled User/Group Status

User and Group status is now enforced

### Improved root Password Reset Utility

CLI reset of root user no longer requires waiting the lockout period to expire

# Version 3.035

## Features

### Quick Clear Restart

Status page list of triggers now supports right click to clear startChecks which will restart a trigger

### Replaced Save / Error Alerts

Save dialogs now appear down the bottom right of the screen instead of as banners

![image](https://user-images.githubusercontent.com/66521110/133906645-737cb73b-44c8-4f48-b692-57509d490271.png)

![image](https://user-images.githubusercontent.com/66521110/133906649-2f1c1d2f-282c-47d0-99cb-12736eaf4cc3.png)

### Bug Fixes

* Cluster Restarting Trigger Failures No Longer Missing from Status Table

# Version 3.034

## Features

### Object Revisions

Changes made to objects are now stored within the revision system to enable quick and simple restore of previous versions.

Within ConductsEditor right click on an object and select "Revision History"

### Trigger Statistics

Viewable last 100 execution times for a trigger

Within ConductsEditor right click on an object and select "Statistics"

![image](https://user-images.githubusercontent.com/66521110/133906629-e6a9c087-7068-4c58-9503-1befaefa55f1.png)

# Version 3.0

Welcome to jimi version 3. 

![image](https://user-images.githubusercontent.com/66521110/133906607-b8a11890-ac9a-419b-9074-1dbe41bea245.png)

This release brings with it major changes both within the backend and frontend UI:

* Updated UI older react interface is now fully removed
* Improved flow performance
* Sub system processes to maximize CPU on multi-processor systems 
* forEach concurrency
* System API security options
* Trigger execution count
* Updated authentication and authorization system
* Advanced debug system
* Better system memory handling 
* Settings moved from settings.json to model editor
* File object storage
* Themes
* Additional system functions
* Moved to integrated webserver cherryPi
* Many many more bug fixes
