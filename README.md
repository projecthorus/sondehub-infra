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