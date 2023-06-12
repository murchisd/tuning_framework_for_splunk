# Tuning Framework for Splunk

## App Properties 
author: Donald Murchison  
check_for_updates: true  
description: Splunk App to implement tuning mechanisms for Splunk alerts  
id: tuning_framework_for_splunk  
is_visible: 1  
label: Tuning Framework for Splunk  
name: tuning_framework_for_splunk  
version: 1.0.0  

## App Structure 
```
tuning_framework_for_splunk
|--- default
`` |--- app.conf
`` |--- data
`` `` |--- ui
`` `` `` |--- views
`` `` `` `` |--- tuning_framework_add_entry.xml
`` `` `` `` |--- tuning_framework_list_entry.xml
`` |--- macros.conf
`` |--- savedsearches.conf
|--- lookups
`` |--- rba_risk_score_override.csv
`` |--- time_based_suppression.csv
|--- README.md
```
## App Confs 
### macros.conf 
#### Default 
```
[tf_time_based_suppression(1)]
definition = | search NOT [| inputlookup time_based_suppression_lookup.csv | eval field=if(key_type="single",split(field,"|"),field) | mvexpand field | eval field=split(field,"|"), value=split(value,"|"), rule_name=split(rule_name,"|") | search rule_name=$rule_name$ | eval combined=if(key_type="single",mvmap(value,field."=\"".value."\""),mvzip(field,mvmap(value,"\"".value."\""),"=")), partial_search=if(key_type="single",mvjoin(combined," OR "), mvjoin(combined," AND ")) | eval partial_search="(".partial_search.")" | stats values(partial_search) as partial_search | eval search=mvjoin(partial_search, " OR ") | eval search="(".search.")" | fields search]
args = rule_name
description = Generates search string for exclusions based on time_based_suppression_lookup.csv

[tf_rba_risk_score_override(1)]
definition = | eval rule_override=[| inputlookup rba_risk_score_override.csv | eval id=sha1(created_time."|".operator."|".field."|".value) | eval field=if(key_type="single",split(field,"|"),field) | mvexpand field | eval field=split(field,"|"), value=split(value,"|"), rule_name=split(rule_name,"|") | search rule_name=$rule_name$ | eval first_subnet=mvfind(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$") | eval second_subnet=mvfind(mvindex(value,first_subnet+1,-1),"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$")+first_subnet+1 | eval cidr_indexes=mvappend(first_subnet,second_subnet) | eval cidr_fields=mvmap(cidr_indexes,mvindex(field,cidr_indexes)) | eval combined=if(key_type="single",mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),"cidrmatch(".field.",\"".value."\")","lower(".field.")=\"".value."\"")),mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(".field,"lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",\"".value."\")","=\"".value."\"")),"")), partial_statement=if(key_type="single",mvjoin(combined," OR "), mvjoin(combined," AND ")) eval partial_statement=partial_statement.",\"".coalesce(score_override,"10")."|".id."\"" | stats values(partial_statement) as partial_statement | eval case="case(".mvjoin(partial_statement, ",").",true(),risk_score)"| appendpipe [|stats count | where count=0 | eval case="risk_score"] | return $case] | rex field=rule_override "(?<risk_score>\d+)\|(?<tuning_entry_id>.*)"
args = rule_name



```
### savedsearches.conf 
#### Default 
```
[time_based_suppression_list_clean_up]
search = | inputlookup time_based_suppression.csv | eval remove=if(relative_time(strptime(created_time,"%s"),"+".suppression_period)<now(),1,0) | eval remove=if(relative_time(strptime(created_time,"%s"),"+180d")<now(),1,remove) | search remove=0 | outputlookup time_based_suppression.csv
dispatch.earliest_time = -5m
dispatch.latest_time = now
cron_schedule = 0 1 * * *
disabled = 0

[rba_confidence_override_list_clean_up]
search = | inputlookup rba_confidence_override.csv | eval remove=if(relative_time(strptime(created_time,"%s"),"+".suppression_period)<now(),1,0) | eval remove=if(relative_time(strptime(created_time,"%s"),"+180d")<now(),1,remove) | search remove=0 | outputlookup rba_confidence_override.csv
dispatch.earliest_time = -5m
dispatch.latest_time = now
cron_schedule = 5 1 * * *
disabled = 0
```