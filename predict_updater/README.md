This Lambda function will execute every minute to update the predictions in the ElasticSearch database.


Dev notes
--
```
index : predict-YYYY-MM
fields :
    serial
    type
    subtype

    datetime
    position
    altitude
    
    ascent_rate
    descent_rate
    burst_altitude
    descending: bool
    landed: bool
    data: object
``