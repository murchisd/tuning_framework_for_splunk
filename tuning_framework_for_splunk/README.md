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
`` `` `` |--- nav
`` `` `` `` |--- default.xml
`` `` `` |--- views
`` `` `` `` |--- tuning_framework_add_entry.xml
`` `` `` `` |--- tuning_framework_list_entry.xml
`` |--- macros.conf
`` |--- savedsearches.conf
`` |--- transforms.conf
|--- lookups
`` |--- rba_risk_score_override_lookup.csv
`` |--- time_based_suppression_lookup.csv
|--- metadata
`` |--- default.meta
|--- README.md
```
## App Confs 
### macros.conf 
#### Default 
```
[tf_time_based_suppression(1)]
definition = | search NOT [| inputlookup time_based_suppression_lookup | eval field=if(operator="or",split(field,"|"),field) | mvexpand field | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") | search rules=$rule_name$ | eval combined=if(operator="or",mvmap(value,field."=\"".value."\""),mvzip(field,mvmap(value,"\"".value."\""),"=")), partial_search=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) | eval partial_search="(".partial_search.")" | stats values(partial_search) as partial_search | eval search=mvjoin(partial_search, " OR ") | eval search="(".search.")" | fields search]
args = rule_name
description = Generates search string for exclusions based on time_based_suppression_lookup.csv

[tf_rba_risk_score_override(1)]
definition = | eval rule_override=[| inputlookup rba_risk_score_override_lookup | eval id=sha1(created_time."|".operator."|".field."|".value) | eval field=if(operator="or",split(field,"|"),field) | mvexpand field | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") | search rules=$rule_name$ | eval first_subnet=mvfind(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$") | eval second_subnet=mvfind(mvindex(value,first_subnet+1,-1),"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$")+first_subnet+1 | eval cidr_indexes=mvappend(first_subnet,second_subnet) | eval cidr_fields=mvmap(cidr_indexes,mvindex(field,cidr_indexes)) | eval tmp_field=field, tmp_value=value | eval combined=if(operator="or",mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),"cidrmatch(\"".value."\",".field.")","like(lower(".field."),\"".value."\")")),mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(\"".mvindex(value,tonumber(mvfind(tmp_field,field)))."\"","like(lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",".mvindex(field,tonumber(mvfind(tmp_value,value))).")",",\"".value."\")")),"")), partial_statement=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) | eval partial_statement=partial_statement.",\"".coalesce(risk_score,"10")."|".id."\"" | stats values(partial_statement) as partial_statement | eval case="case(".mvjoin(partial_statement, ",").",true(),risk_score)"| appendpipe [|stats count | where count=0 | eval case="risk_score"] | return $case] | rex field=rule_override "(?<risk_score>\d+)\|(?<tuning_entry_id>.*)" | fields - rule_override
args = rule_name



```
### savedsearches.conf 
#### Default 
```
[TF_R_0001-Tuning_Framework_Risk_Score_Override_Lookup_Cleanup]
search = | inputlookup rba_risk_score_override_lookup | eval remove=if(relative_time(strptime(created_time,"%s"),"+".suppression_period)<now(),1,0)| search remove=0 | fields - remove | outputlookup rba_risk_score_override_lookup
dispatch.earliest_time = -5m
dispatch.latest_time = now
cron_schedule = 7-59/15 * * * *
disabled = 0

[TF_R_0002-Tuning_Framework_Time_Based_Suppression_Lookup_Cleanup]
search = | inputlookup time_based_suppression_lookup | eval remove=if(relative_time(strptime(created_time,"%s"),"+".suppression_period)<now(),1,0)| search remove=0 | fields - remove | outputlookup time_based_suppression_lookup
dispatch.earliest_time = -5m
dispatch.latest_time = now
cron_schedule = 4-59/15 * * * *
disabled = 0

```
### transforms.conf 
#### Default 
```
[time_based_suppression_lookup]
filename = time_based_suppression_lookup.csv

[rba_risk_score_override_lookup]
filename = rba_risk_score_override_lookup.csv
```
