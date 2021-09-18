# Version 3.037

## Improved - Theme Selection

My Account now includes a dropdown menu for theme selection. No more guessing what the theme names are

## Improved - Storage 

Added UI options for file tokens and downloading of already uploaded files

## Improved - Object Revisions

Object revision UI is no longer in BETA and now is officially released. As part of this release the UI has been updated to include the revision creator as well as a view button that enables you to see the content of the revision without restoring the object

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

# Version 3.0

Welcome to jimi version 3. 

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
