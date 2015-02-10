library(httr)
library(RJSONIO)
library(ISOweek)
library(bit64)

ES_URI_MWT2 <- "http://uct2-es-head.mwt2.org:9200"
ES_URI_LOCAL <- "http://localhost:8000"

queryES <- function(index, query_dsl, cluster_uri) {
  query_url = paste(cluster_uri, '/', index, '/_search', sep="")
  response <- POST(query_url, body=query_dsl)
  return(response)
}

getAverages <- function(start_date, end_date, cluster_uri=ES_URI) {
  start_time <- as.POSIXct(paste(start_date, " ", "00:00:00"), tz="UTC")
  end_time <- as.POSIXct(paste(end_date, " ", "00:00:00"), tz="UTC")
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
    range_start <- as.integer64(day) * 1000
    range_end <- range_start + 86400000
    my_query <- sub('start_time', c(as.character(range_start)), query_dsl)
    my_query <- sub('end_time', c(as.character(range_end)), my_query)
    iso_week <- as.integer(substring(ISOweek(as.POSIXct(day, origin="1970-01-01", tz="UTC")), 7))
    index <- paste('jobsarchived_2014_', iso_week - 3, ',',
                   'jobsarchived_2014_', iso_week - 2, ',',
                   'jobsarchived_2014_', iso_week - 1, ',',
                   'jobsarchived_2014_', iso_week, sep="")
    results <- content(queryES(index, my_query, cluster_uri))
    doc_count[i] <- results$hits$total
    print(as.POSIXct(day, origin="1970-01-01", tz="UTC"))
    if (results$hits$total > 0) {
      queue_avg[i] <- results$aggregations$queue_avg$value
      script_avg[i] <- results$aggregations$script_avg$value / 1000
    } else {
      queue_avg[i] <- NA
      script_avg[i] <- NA
    }
    i <- i+1    
  }
  return(data.frame(date = date, 
                    document_count = doc_count,
                    script_avg = script_avg,
                    queue_avg = queue_avg))
}

getAverages_test <- function(start_date, end_date, cluster_uri=ES_URI) {
  start_time <- as.POSIXct(paste(start_date, " ", "00:00:00"), tz="UTC")
  end_time <- as.POSIXct(paste(end_date, " ", "00:00:00"), tz="UTC")
  query_dsl <- '{"query": {
                    "filtered" : {
                        "query": {
                          "query_string" : {
                            "query" : "*"
                          }
                        },
                        "filter": {
                          "bool": {
                            "must": [
                              {"range":
                                {"MODIFICATIONTIME":
                                  {"gte": start_time,
                                   "lt": end_time}}},
                              {"exists" : { "field": "CREATIONTIME" }},
                              {"exists" : { "field": "STARTTIME" }}]}}}},
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
    range_start <- as.integer64(day) * 1000
    range_end <- range_start + 86400000
    my_query <- sub('start_time', c(as.character(range_start)), query_dsl)
    my_query <- sub('end_time', c(as.character(range_end)), my_query)
    iso_week <- as.integer(substring(ISOweek(as.POSIXct(day, origin="1970-01-01", tz="UTC")), 7))
    index <- paste('jobsarchived_2014_', iso_week - 3, ',',
                   'jobsarchived_2014_', iso_week - 2, ',',
                   'jobsarchived_2014_', iso_week - 1, ',',
                   'jobsarchived_2014_', iso_week, sep="")
    results <- content(queryES(index, my_query, cluster_uri))
    print(as.POSIXct(day, origin="1970-01-01", tz="UTC"))
#     print(results$aggregations$queue_avg$value)
#     print(results$aggregations$script_avg$value)
#     print(results$hits$total)
    doc_count[i] <- results$hits$total
    if (results$hits$total > 0) {
      queue_avg[i] <- results$aggregations$queue_avg$value
      script_avg[i] <- results$aggregations$script_avg$value / 1000
    } else {
      queue_avg[i] <- NA
      script_avg[i] <- NA
    }
    i <- i+1    
  }
  return(data.frame(date = date, 
                    document_count = doc_count,
                    script_avg = script_avg,
                    queue_avg = queue_avg))
}


get_hadoop_results <- function() {
  hadoop_results <- read.csv("~/tmp/jobrecord-comparison/waitGperDay-fixed_date.csv")  
  colnames(hadoop_results) <- c('date', 'queue_avg', 'day_of_year')
  hadoop_results$date <- as.POSIXct(hadoop_results$date, origin="1970-01-01 00:00.00", tz="GMT")
  hadoop_results_sorted <- hadoop_results[order(hadoop_results$date),]
  return(hadoop_results)
}

get_python_results <- function() {
  csv_data <- read.csv("~/tmp/jobrecord-comparison/python-averages.csv")
  colnames(csv_data) <- c('date', 'queue_avg', 'script_avg', 'document_count')
  csv_data$date <- as.POSIXct(csv_data$date, origin="1970-01-01 00:00.00", tz="GMT")
  trimmed_data <- csv_data[csv_data$date >= "2014-06-30" & csv_data$date <= "2014-11-03",]
  return(trimmed_data)
}

get_R_results <- function() {
  results <- getAverages('2014-07-01', '2014-11-03')
  return(results)
}

get_job_counts <- function(python_results) {
  csv_data <- read.csv("~/tmp/jobrecord-comparison/job_counts.csv")
  colnames(csv_data) <- c('date', 'day', 'hadoop_job_counts', '')
  csv_data$date <- as.POSIXct(csv_data$date, origin="1970-01-01 00:00.00", tz="GMT")
  start_date <- as.POSIXct('2014-07-01', origin="1970-01-01 00:00.00", tz="GMT")
  end_date <- as.POSIXct('2014-11-03', origin="1970-01-01 00:00.00", tz="GMT")
  vec_length <- max(length(csv_data$date), length(python_results$date))
  dates <- numeric(vec_length)
  csv_count <- numeric(vec_length)
  python_count <- numeric(vec_length)
  r_count <- numeric(vec_length)
  index <- 1
  for (i in seq(start_date, end_date, by='day')) { 
    csv_select <- csv_data$date == as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT")
    python_select <- python_results$date == as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT") 
    r_select <- r_results$date == as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT") 
    dates[index] <- as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT")
    count <- csv_data[csv_select,]$hadoop_job_count
    if (!is.na(count) && (length(count) != 0)) {
      csv_count[index] <- count
    } else {
      csv_count[index] <- NA
    }
    count <- python_results[python_select,]$document_count
    if (!is.na(count) && (length(count) != 0)) {
      python_count[index] <- count
    } else {
      python_count[index] <- NA
    }
    count <- r_results[r_select,]$document_count
    if (!is.na(count) && (length(count) != 0)) {
      r_count[index] <- count
    } else {
      r_count[index] <- NA
    }
    index <- index + 1
  }  
  return(data.frame(date=as.POSIXct(dates, origin="1970-01-01 00:00.00", tz="GMT"), 
                    hadoop_job_count=csv_count, 
                    python_job_count=python_count))
  
}

compare_queue_times <- function(hadoop, python) {
  start_date <- as.POSIXct('2014-07-01', origin="1970-01-01 00:00.00", tz="GMT")
  end_date <- as.POSIXct('2014-11-03', origin="1970-01-01 00:00.00", tz="GMT")
  dates <- numeric(max(length(hadoop$date),
                       length(python$date)))
  diff <- numeric(max(length(hadoop$date),
                      length(python$date)))
  index <- 1
  for (i in seq(start_date, end_date, by='day')) { 
    hadoop_select <- hadoop$date == as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT")
    python_select <- as.POSIXct(python$date, tz="UTC") == i
    time_difference <- hadoop[hadoop_select,]$queue_avg - 
      python[python_select,]$queue_avg
    if ((length(time_difference) > 0) && !is.na(time_difference)) {
      dates[index] <- as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT")
      diff[index] <- time_difference
      index <- index + 1
    } else {
      dates[index] <- as.POSIXct(i, origin="1970-01-01 00:00.00", tz="GMT")
      diff[index] <- 0
      index <- index + 1      
    }
  }
  return(data.frame(date=as.POSIXct(dates, origin="1970-01-01"), 
                    difference=diff))
}