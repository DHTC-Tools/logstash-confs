library(httr)
library(RJSONIO)
library(ISOweek)

ES_URI = "http://uct2-es-head.mwt2.org:9200"

queryES <- function(index, query_dsl) {
  query_url = paste(ES_URI, '/', index, '/_search', sep="")
  response <- POST(query_url, body=query_dsl)
  return(response)
}

getAverages <- function(start_date, end_date) {
  start_time <- as.POSIXct(paste(start_date, " ", "00:00:00"))
  end_time <- as.POSIXct(paste(end_date, " ", "00:00:00"))
  query_dsl <- '{"query": {
                    "filtered" : {
                        "filter": {
                          "bool": {
                            "must": [
                              {"range":
                                {"MODIFICATIONTIME":
                                  {"gte": start_time,
                                   "lt": end_time}}},
                              {"exists" : { "field": "CREATIONTIME" }},
                              {"exists" : { "field": "STARTTIME" }},
                              {"exists" : { "field": "queue_time" }}]}}}},
                   "size": 0,
                   "aggs":  {
                     "queue_avg":
                       {"avg":
                         {"field": "queue_time"}},
                     "script_avg":
                       {"avg":
                         {"script": "doc[\'STARTTIME\'].value - 
                               doc[\'CREATIONTIME\'].value"}}}}'
  query_dsl <- gsub("\n", "", query_dsl)
  date <- seq(start_time, end_time, by='days')
  queue_avg <- numeric(length(date))
  script_avg <- numeric(length(date))
  doc_count <- numeric(length(date))
  i <- 1
  for (day in seq(start_time, end_time, by='days')) {
    range_start <- as.numeric(day) * 1000
    range_end <- range_start + 86400000
    my_query <- sub('start_time', c(as.character(range_start)), query_dsl)
    my_query <- sub('end_time', c(as.character(range_end)), my_query)
    iso_week <- as.integer(substring(ISOweek(as.POSIXct(day, origin="1970-01-01")), 7))
    index <- paste('jobsarchived_2014_', iso_week - 1, ',',
                   'jobsarchived_2014_', iso_week, sep="")
    results <- content(queryES(index, my_query))
    doc_count[i] <- results$hits$total
    queue_avg[i] <- results$aggregations$queue_avg$value
    script_avg[i] <- results$aggregations$script_avg$value / 1000
    i <- i+1    
  }
  return(data.frame(date = date, 
                    document_count = doc_count,
                    script_avg = script_avg,
                    queue_avg = queue_avg))
}