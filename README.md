# AM43-python-controller

=============
Cross-platform controller for the AM43 blind motor

## Table of Contents

- [Project Background](#project-background)
- [Install & Setup](#install-&-setup)
- [Usage](#usage)
- [Endpoints](#endpoints)
- [Authors](#authors)
- [License](#license)

## Project Background

The AM43 blind motor has a terrible mobile app and it would be nice to control these devices using simple api calls to a RPI with BLE to tie into a home automation platform.

## Install & Setup

Install using:
`pip install -r requirements.txt`

## Usage

Run using:
`flask run --host=0.0.0.0`

On first run you'll get a prompt to add blinds to the DB, you'll need your blind's mac address to do this. If you'd like to run the setup process again just remove the generated am43.db file. 

To have this app run on startup, I recommend setting up a service after initial setup:

_On Raspberry Pis_
1. Create a service like the one in this repo: 
    - `sudo nano /etc/systemd/system/blind_controller.service`
2. Save and chmod the service and verify it starts correctly: 
    - `sudo systemctl start blind_controller.service`
    - `sudo systemctl status blind_controller.service`
3. Then just enable your service:
    - `sudo systemctl enable blind_controller.service`

## Endpoints

|Endpoint |Parameters | Description|
--- | --- | --- |
|POST /blinds| `mac_address` <br> `name`| Old endpoint to add blinds to the system|
|GET /blinds | none | Returns the `name`, `mac_address`, `battery`, `position`, and `light` of all blinds currently in the system|
|POST /blinds/set| `position` <br> `mac_address` *optional* | Sets all blinds in the system to the value of `position` (0-100) or can set the position of single blind when `mac_address` is given|
|GET /blinds/update| none | Pings all blinds in system for device properties then updates the DB

## Authors

- Zac Adams | [@ZacTyAdams](https://github.com/ZacTyAdams)

## License

