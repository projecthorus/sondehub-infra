# SondeHub

Sondehub aggregates telemetry data that is uploaded from community run radiosonde receiver stations (currently only [radiosonde_auto_rx](https://github.com/projecthorus/radiosonde_auto_rx/wiki) though others are welcome to contribute!). Weather balloons are launched from numerous weather organisations around the world, with the data used to build weather models such as the [GFS](https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/global-forcast-system-gfs) and [ECMWF](https://www.ecmwf.int/). The goal of SondeHub is collect the community-sourced data in a central location to allow organisations to develop their own models and forecasting, and to assist hobbyists in the recovery of the radiosondes themselves (which are otherwise discarded).

Sondehub is based around Amazon-Web-Services (AWS), and this repository serves as a place to configure the various configuration scripts and lambdas (Python scripts) that are used to keep Sondehub running. The wiki section of this repository is currently serving as a temporary API reference, until a better solution is set up.

**Refer to the Wiki page for the latest information: https://github.com/projecthorus/sondehub-infra/wiki**

## Contacts
* [Mark Jessop](https://github.com/darksidelemm) - vk5qi@rfhead.net
* [Michaela Wheeler](https://github.com/TheSkorm) - radiosonde@michaela.lgbt

You can often find us in the #highaltitude IRC Channel on
[Freenode](https://webchat.freenode.net/).


WIP
==
todo
--
 - Most of this was generated using former2, so it's very rough, need to rename things to make sense
 - lambda layers should be scripted so we can deploy them again (or at the least documented), or move to packaging them into the deployable
 - all the sondehub v1 stuff needs migrating, rebuilding
   - web interface
   - basic APIs
 - build out APIs for sondehub ui replacement
 - we don't have rate limiting ? do we need it
 - cognito needs to be setup to allow private access
 - replace profile defination with env variables since not all admins will have that profile
 - add in DLQ for ingest, and for elk
 - add a way to process DLQ
 - monitor on stuff going into DLQ
 - cloudfront distribution and route53 enteries to map