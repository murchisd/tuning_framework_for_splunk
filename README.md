# Tuning Framework Overview

The Tuning Framework is a custom framework built in Splunk to facilitate tuning detection rules to suppress false positives or adjsut risk score for Risk Based Alerting. The framework implements a small number of lookups and macros to dynamically suppress events or adjust risk scores for all correlation searches based on any combination of fields within the events. For most Splunk environemnts, this will enhance analysts ability to quickly tune rules and greatly reduce the lift from Splunk administrators.
  
Analysts can use the `Add Entry` dashboard to add a combination of correlation search names, fields, and values to tuning lookups which will be used to suppress or adjust risk score for any events that match the specified criteria. This is done by constructing dynamic chunks of SPL to form searches and eval statements based on the contents of the lookups. By doing this, we can use a single lookup for tuning all correlation searches without having to anticipate the different combinations of fields analyst may need to match on. The risk score adjustment works whether you have implemented a macor based version of RBA or are using the Risk Analysis adaptive response action.  
  
Entries in the lookups have a maximum lifetime of 180 days, but this can be set as part of the `Add Entry` dashboard. Analysts can also remove entries at anytime by finding the entry in the `List/Remove Entry` dashboard and clicking `Click to Remove` in the appropriate row. 
  
This documentation will describe how to use the framework, the components of the framework, and the details of the SPL logic used to produce the dynamic searches and evals.

## Installing and Configuring the Tuning Framework

Setting up the framework is very simple and only requires two steps:

1. Install the `Tuning Framework for Splunk` App
1. Add Tuning Macros to Correlation Searches


That's it! Once these steps are complete, analysts will be able to suppress or adjust risk scores across any correlation search based on any combination of fields within the events, with no other configuration from Splunk admins.  

### 1. Installing the Tuning Framework for Splunk App

* Download the tuning_framework_for_splunk.tgz file from Splunkbase(to-do) or Github
  * [Github](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/tuning_framework_for_splunk.tgz)
  * Splunkbase - to-do
  
* Install App from file
  * Navigate to Splunk instance
  * Select `Manage Apps -> Install app from file -> Choose File` and select the tuning_framework_for_splunk.tgz 

### 2. Add Tuning Macros to Correlation Searches 

The framework uses a macro to suppress events, `tf_time_based_suppression(1)`, and one to adjust risk scores, `tf_rba_risk_score_override(1)`. These macros must be added to the correlation searches and passed the search name as an argument to enable the corresponding capability. **Position of the macros matters.** In most cases, the macros should be added to the very end of the search.  
  
For example, assume there is a correlation search `Authentication - RR - Excessive Failed Logins` which I would like to enable both suppression and risk score adjustment capabilities. The SPL for the search is listed below.

````
| tstats count from datamodel=Authentication where Authentication.action="failure" by Authentication.user 
| rename Authentication.* as *
| search count > 10
````

I would add both macros to the end of the SPL as seen below. The below example will run a `| eval risk_score=...` followed by a `| search NOT ...` after the `|search count > 10`.

````
| tstats count from datamodel=Authentication where Authentication.action="failure" by Authentication.user 
| rename Authentication.* as *
| search count > 10
`tf_rba_risk_score_override("Authentication - RR - Excessive Failed Logins")`
`tf_time_based_suppression("Authentication - RR - Excessive Failed Logins")`
````

One instance where you would not add to the end of the SPL is when using `collect` or `sendalert` to write you own risk events. You would want to place the macros before either of these commands.

````
| tstats count from datamodel=Authentication where Authentication.action="failure" by Authentication.user 
| rename Authentication.* as *
| search count > 10
| eval risk_score="20"
`tf_rba_risk_score_override("Authentication - RR - Excessive Failed Logins")`
`tf_time_based_suppression("Authentication - RR - Excessive Failed Logins")`
| collect index=risk 
````

## Using the Tuning Framework

To use the framework, analysts only need two functions, adding entries and removing entries. These actions can be performed using the `Add Entry` and `List/Remove Entry` dashboards.

### Add Entries to the Tuning Lookups

The simplest way to add entries to the tuning lookups is to use the `Add Entry` dashboard. To do this, select or fill in the appropriate inputs and click `Submit`. Detailed documentation about each input and the resulting tuning behavior is included on the `Add Entry` dashboard and in the `Framework Logic` section below. 

![Add Entry Dashboard](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/add_entry_dashboard.png)

The following screen shots show an example of adding an entry which will suppress any events where `src` OR `src_ip` equals `10.0.0.1` or an IP in `192.168.0.1/16` range for `Authentication - RR - Excessive Failed Logins` rule. This example would create an entry in the tuning lookups that the tf_time_based_suppression macro would evaluate to add `| search NOT ((src=10.0.0.1 OR src=192.168.0.1/16) OR (src_ip=10.0.0.1 OR src_ip=192.168.0.1/16))` to the end of the `Authentication - RR - Excessive Failed Logins` rule.

1. Select `Suppression` Tuning Mode and `Authentication - RR - Excessive Failed Logins` from the Correlation Searches drop down

  ![tuning mode and correlation search name input screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/tuning_mode_and_cs_name_input.png)

2. Specify Pipe Delimited Fields and Values for Suppression `src|src_ip` and `10.0.0.1|192.168.0.1/16`

  ![field and value input screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/field_and_value_input.png)

3. Select Lifetime and Logic Operator and specify Notes (Risk Score input is not used for Suppression Tuning Mode)

  ![lifetime_operator_notes_input screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/lifetime_operator_notes_input.png)

4. Suppress Warnings if necessary 

  Certain checks have been put in place to ensure proper format of entries and that analysts are aware of the resulting behavior. This example generates the warning `Warning: "value" input contains a pipe for Logic Operator "OR" - Multiple values will be suppressed using pipe delimiter - Verify this is desired behavior - select ignore warnings to suppress this message`. Warnings can be bypassed by setting `Ignore Warnings` to `Yes`.

  ![warning screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/warning.png)

5. Select `Run Query`

  After ignoring any warnings, you need to perform one final action before the entry will be added. Splunk has implemented safegaurds against "risky" SPL commands ([documentation](https://docs.splunk.com/Documentation/Splunk/latest/Security/SPLsafeguards#SPL_safeguards_for_risky_commands)). This means the `OUTPUTLOOKUP` will not run without user interaction. You must select the `red square` at the bottom right of the `Tuning Output Lookup Action` panel and select `Run Query`.

  ![potentially_risky_command screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/potentially_risky_command.png)

  ![run_query screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/run_query.png)

6. Success!
  The entry should have been successfully added to the Tuning Framework

  ![successfully_added_entry screenshot](https://github.com/murchisd/tuning_framework_for_splunk/blob/main/static/successfully_added_entry.png)

## Tuning Framework Components

The framework is built using a collection of lookups, saved searches, dashboards, and macros. Details about the individual components are below:

### Lookups
* time_based_suppression_lookup.csv 
  * Fields: created_time,field,value,rules,operator,lifetime,notes
* rba_risk_score_override_lookup.csv
  * Fields: created_time,field,value,rules,operator,lifetime,notes,risk_score

### Lookup Definitions
* time_based_suppression_lookup
  * Advanced Configurations: None
* rba_risk_score_override_lookup 
  * Advanced Configurations: None

### Saved Searches
* TF_R_0001-Tuning_Framework_Risk_Score_Override_Lookup_Cleanup - remove entries that have expired from rba_risk_score_override_lookup
* TF_R_0002-Tuning_Framework_Time_Based_Suppression_Lookup_Cleanup - remove entries that have expired from time_based_suppression_lookup

### Dashboards
* Add Entry - Dashboard allows analysts to add entries to the tuning lookups. The Dashboard performs error checking against the user input to ensure that all entries are formatted correctly. Certain format checks will present an error that analysts cannot override while others just warn the analysts and allow them to override. Further details about dashboard are provided on the Dashboards README.
* List/Remove Entry- Dashboard allows analysts to query and remove entries from the tuning lookups. Analysts can search across rule id, rule name, fields, and values to find a specific entry. Further details about dashboard are provided on the Dashboards README.

### Macros
* tf_time_based_suppression
* tf_rba_risk_score_override

## Framework Logic

The lookups and macros serve as the foundation of this framework. The lookup consists of the details for each tuning entry and the macros convert those details to SPL. There are two types of tuning, `Suppression` and `Risk Score Override`. `Suppression` will create a search string to exclude events matching the specified criteria. `Risk Score Override` will create an eval statement to set `risk_score` field based on the specified criteria.
  
You can specify either `OR` or `AND` logic operators for entries in the framework. `OR` operator will create SPL that matches all combinations of fields and values listed. The `AND` operator will create SPL that matches only whan all fields equal their corresponding value. For example, assume the tuning mode was `suppression`, field column was `src|src_ip`, and the value column was `test.local|10.0.0.1`. 

* `OR` would produce the following SPL `((src=test.local OR src=10.0.0.1) OR (src_ip=test.local OR src_ip=10.0.0.1))`. 
* `AND` would produce the following SPL `(src=test.local AND src_ip=10.0.0.1)`


### Suppression Macro

Currently, there is only one suppression macro (listed below). This will create a `| search NOT` SPL string to exclude events that match the specified criteria.

* tf_time_based_suppression(1)

The full SPL for `tf_time_based_suppression` is shown below. It consists of an inner search which builds the SPL for the exclusions and an outer search which just runs `|search NOT <inner search results>`.

````
| search NOT 
    [| inputlookup time_based_suppression_lookup.csv 
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field 
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | search rules=$rule_name$ 
    | eval combined=if(operator="or",mvmap(value,field."=\"".value."\""),mvzip(field,mvmap(value,"\"".value."\""),"=")), partial_search=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_search="(".partial_search.")" 
    | stats values(partial_search) as partial_search 
    | eval search=mvjoin(partial_search, " OR ") 
    | eval search="(".search.")" 
    | fields search]
````

The inner search first uses `inputlookup` to generate events with the contents of the tuning lookup. The next step splits `field` into a multivalue field but only for `OR` operator entries.

````
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field  
````    
 By doing this, we can use mvexpand to create a new event for every field specified. This simplifies the logic for creating the SPL because now every `OR` entry actually only references a single field. For example, assume the field column was `src|src_ip` and the value column was `test.local|10.0.0.1`. This becomes  

| Field | Value |
| ----- | ----- |
| src | test.local&#124;10.0.0.1|
| src_ip | test.local&#124;10.0.0.1|

Next we simply convert `field` (only applies to `AND` because of above steps), `value`, and `rules` to multivalue fields by splitting on pipe. We can then filter entries for only those that match the `rule_name` passed as an argument to the macro. 
  
````
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | search rules=$rule_name$
````

The SPL below creates the majority of the dynamic SPL for the output search. First an intermediate field called `combined` is created by mapping `field` column to `value` column to create <field>=<value>. For `OR` entries, mvmap is used to prepend each value with `<field>=`. mvmap is an eval function that iterates over the values of a multivalue field and performs an operation on each value. For `AND` entries, mvzip is used to map corresponding field and values to each other. mvzip is an eval function that combines the values in two multivalue fields (there is an optional argument for delim which we use here). Due to limitations in mvzip, a nested mvmap is required to wrap the value in quotes. After the `combined` field is created it is joined with `OR` or `AND` and wrapped in parentheses to create the `partial_search` field. 

````
    | eval combined=if(operator="or",mvmap(value,field."=\"".value."\""),mvzip(field,mvmap(value,"\"".value."\""),"=")), partial_search=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_search="(".partial_search.")"
````

The table below shows the output for the example of `src|src_ip` and `test.local|10.0.0.1` (one entry for `OR` and one entry for `AND`).

| Operator | Field | Value | Combined | Partial Search |
| -------- | ----- | ----- | -------- | -------------- |
| OR | src | test.local <br> 10.0.0.1 | src="test.local" <br> src="10.0.0.1" | (src="test.local" OR src="10.0.0.1") |
| OR | src_ip | test.local <br> 10.0.0.1 | src_ip="test.local" <br> src_ip="10.0.0.1" | (src_ip="test.local" OR src_ip="10.0.0.1") |
| AND | src <br> src_ip | test.local <br> 10.0.0.1 | src="test.local" <br> src_ip="10.0.0.1" | (src="test.local" AND src="10.0.0.1") | 


Finally, the macro combines all of the `partial_search` fields into one multivalue field and then joins them with `OR`, wraps everything in parentheses, and returns the field as search to be used in the outer search.

````
    | stats values(partial_search) as partial_search 
    | eval search=mvjoin(partial_search, " OR ") 
    | eval search="(".search.")" 
    | fields search
````
 The final result of the inner search combined with the outer search for the example above is

` | search NOT ((src="test.local" OR src="10.0.0.1") OR (src_ip="test.local" OR src_ip="10.0.0.1") OR (src="test.local" AND src="10.0.0.1")) `

#### Stress Test
Stress test for the suppression macro is done to determine if there is a maximum number of entries or length of string that can be returned before the subsearch no longer works. To perform a stress test we duplicate the partial_search multivalue field prior to constructing the search field, then append a single exclusion entry with our test field. An example of this search is shown below:
````
|makeresults 
| eval test_field="test"
| search NOT 
    [| inputlookup time_based_suppression_lookup.csv 
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field  
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | eval combined=if(operator="or",mvmap(value,field."=\"".value."\""),mvzip(field,mvmap(value,"\"".value."\""),"=")), partial_search=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_search="(".partial_search.")" 
    | stats values(partial_search) as partial_search  
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,partial_search)
    | eval partial_search=mvappend(partial_search,"(test_field=\"test\")")
    | eval search=mvjoin(partial_search, " OR ") 
    | eval search="(".search.")"
    | fields search]
````

The results of our tests are below. The results of these tests our indicative of how tuning would perform if a single rule had this many tuning entries, not if the entire lookup had this many entries. This type of test does not perform any tests for overall size of lookup and effects on the knowledge bundle. The tuning lookup should never come close in size to some of our other lookups, like `local_threatconnect_indicators` so we did not test this.

| Number of Entries | Length of Search | Time to Evaluate | Result |
|-------------------|------------------|------------------|--------|
| 28865 | 1.5 MB | 2.5s | Successful |
| 57729 | 3 MB | 10s | Successful |
| 115457 | 6 MB | 22s | Successful |
| 230913 | 12 MB | 157s | Successful |

From these tests, we see performance degradation starting around 30,000 entries with significant degradation around 200,000. However, the macro still correctly suppresses the test entry. This testing shows our tuning framework should be suficient for our use case, especially considering our current tuning list size contains 500 entries total (across all rules). 

### Risk Score Macro

Currently, there is only one risk score macro. This will create a dynamic eval command to override the `risk_score` field and create a `tuning_entry_id` field. `tuning_entry_id` allows analysts to easily lookup the entry that matched for each event. The `risk_score` field is hardcoded but the current macro could easily be updated to accept the field name to override as an argument.

* tf_rba_risk_score_override(1)
  
The full SPL for `tf_rba_risk_score_override` is shown below. It consists of an inner search which builds the dynamic eval statement and an outer eval statement to run it `| eval risk_score=<inner search results>`.

````
| eval rule_override= 
    [| inputlookup rba_risk_score_override.csv 
    | eval id=sha1(created_time."|".operator."|".field."|".value) 
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field 
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | search rules=$rule_name$ 
    | eval first_subnet=mvfind(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$") 
    | eval second_subnet=mvfind(mvindex(value,first_subnet+1,-1),"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$")+first_subnet+1 
    | eval cidr_indexes=mvappend(first_subnet,second_subnet) 
    | eval cidr_fields=mvmap(cidr_indexes,mvindex(field,cidr_indexes))
    | eval tmp_field=field, tmp_value=value 
    | eval combined=if(operator="or",mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),"cidrmatch(\"".value."\",".field.")","like(lower(".field."),\"".value."\")")),mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(\"".mvindex(value,tonumber(mvfind(tmp_field,field)))."\"","like(lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",".mvindex(field,tonumber(mvfind(tmp_value,value))).")",",\"".value."\")")),"")), partial_statement=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_statement=partial_statement.",\"".coalesce(risk_score,"10")."|".id."\"" 
    | stats values(partial_statement) as partial_statement 
    | eval case="case(".mvjoin(partial_statement, ",").",true(),risk_score)" 
    | appendpipe 
        [| stats count 
        | where count=0 
        | eval case="risk_score"] 
    | return $case] 
| rex field=rule_override "(?<risk_score>\d+)\|(?<tuning_entry_id>.*)"
| fields - rule_override
````

The first part of risk score macro performs the exact same steps as the search macros. The inner search first uses `inputlookup` to generate events with the contents of the tuning lookup, then splits `field` into a multivalue field for the `OR` entries. 

````
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field 
````    

Just as with the suppression macro, this simplifies the logic for creating the SPL because now every `OR` entry only references a single field. For example, assume the `field` column was `src|src_ip` and the `value` column was `test.local|10.0.0.1`. This becomes

| Field | Value |
| ----- | ----- |
| src | test.local&#124;10.0.0.1|
| src_ip | test.local&#124;10.0.0.1|

Next we continue with the same steps as the suppression macro and convert `field` (only applies to `AND` because of above steps), `value`, and `rules` to multivalue fields by splitting on pipe. We can then filter entries for only those that match the `rule_name` passed as an argument to the macro. 

````
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | search rules=$rule_name$ 
````
The next step is to determine if any cidr ranges are specified in the tuning lookup. This is only necessary for `AND` entries and is required because `=` operator (used for all other fields) does not work for cidr ranges within an eval, instead a special operator `cidrmatch` must be used in eval statements. We use `mvfind` to extract the first cidr range in the `value` column. `mvfind` returns the index for the first value in a multivalue field that matches a regular expression. We call `mvfind` a second time on the remaining portion of the `value` column. We could not find a way to dynamically extract all cidr range indexes so this macro only supports two cidr ranges in a single entry. **While it is not likely that there would be a need for more than two cidr ranges this is a limitation to be aware of.** Then, for each of the cidr indexes, we call `mvindex` of the `field` column using mvmap. `mvindex` is an eval function that returns a subset of the multivalue field using the start and end index values and `mvmap` is an eval function that iterates over the values of a multivalue field and performs an operation on each value.

````
    | eval first_subnet=mvfind(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$") 
    | eval second_subnet=mvfind(mvindex(value,first_subnet+1,-1),"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$")+first_subnet+1 
    | eval cidr_indexes=mvappend(first_subnet,second_subnet) 
    | eval cidr_fields=mvmap(cidr_indexes,mvindex(field,cidr_indexes)) 
````

Similar to the suppression macro, the SPL below creates the bulk of the dynamic SPL for the eval statement. First, we create an intermediate field `combined` which consists of a `=` or `cidrmatch` statement for each value in the entry. For `OR`  entries, we iterate over each `value` using mvmap, check if the specific value matches cidr regex, and then either create the `=` or `cidrmatch` statement with the single field value. 

````
    | eval combined=if(operator="or",mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),"cidrmatch(\"".value."\",".field.")","like(lower(".field."),\"".value."\")")),mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(\"".mvindex(value,tonumber(mvfind(tmp_field,field)))."\"","like(lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",".mvindex(field,tonumber(mvfind(tmp_value,value))).")",",\"".value."\")")),"")), partial_statement=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_statement=partial_statement.",\"".coalesce(risk_score,"10")."|".id."\"" 
````

For example, assume operator is `OR`, field is `src`, and value is `10.0.0.1/8|test.local|192.168.0.0/16`. The output would be

| Operator | Field | Value | Combined |
| -------- | ----- | ----- | -------- |
| or | src | 10.0.0.1/8 <br> test.local <br> 192.168.0.0/16 | cidrmatch("10.0.0.1/8",src) <br> lower(src)="test.local" <br> cidrmatch("192.168.0.0/16",src) |

`AND` entries are slightly more complicated because both field and value are multi value fields, so we cannot simply reference `field` when we iterate over `value`. `mvzip`, an eval function that combines the values in two multivalue fields, normally handles this problem nicely, but in this instance we need to prepend text to each `field` value based on the corresponding value in `value` column. There is no standard way to iterate across two fields in Splunk so this is why we created the list of field names which correspond to cidr ranges,`cidr_fields`, previously. The specific SPL to handle this is shown below: 
  
`mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(\"".mvindex(value,tonumber(mvfind(tmp_field,field)))."\"","like(lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",".mvindex(field,tonumber(mvfind(tmp_value,value))).")",",\"".value."\")")),"")`
  
First, we iterate over the `field` column, if the `field` value exists in `cidr_fields`(meaning it corresponds to cidr range) then teh corresponding `value` is prepended with `cidrmatch(` else `field` is wrapped with `lower(...)` and prepended with `like(`. Then we iterate over the `value` column, if the value matches a cidr range wrap the corresponding `field` in `,"...")`, if the value does not match a cidr range then wrap it quotes, prepend with comma, and a parentheses is appened  `,"...")`. Finally, we use `mvzip` to combine the formatted fields. Example using `AND` operator with original field as `src_cidr|test|dest_ip`, and original value as `10.0.0.1/32|test.local|192.168.0.0/16` is shown below

| Operator | Result from iterating Field | Results from iterating Value | Combined |
| -------- | ----- | ----- | -------- |
| or | cidrmatch("10.0.0.1/32" <br> like(lower(test) <br> cidrmatch("192.168.0.0/16" | ,src_cidr) <br> ,"test.local") <br> ,dest_ip) | cidrmatch("10.0.0.1/32",src_cidr) <br> like(lower(test),"test.local") <br> cidrmatch("192.168.0.0/16",dest_ip) |

After this we create a `partial_statement` field which joins the statements with `OR` or `AND` dependent on the operator, and then appends `,"<risk score value>|<tuning entry id>"`. The risk score value is set within the tuning lookup and should always be populated, however we use a coalesce to set default of 10 in case it is null. 
````
    ..., partial_statement=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_statement=partial_statement.",\"".coalesce(risk_score,"10")."|".id."\""
````
The partial statement for the above example should look something like this `cidrmatch("10.0.0.1/32",src_cidr) AND like(lower(test),"test.local") AND cidrmatch("192.168.0.0/16",dest_ip),"<risk score value>|<tuning entry id>"`. After building the partial statements we combine them into a single multivalue field, join them with `,` and create a case statement with default branch setting `risk_score` to itself.

````
    | stats values(partial_statement) as partial_statement 
    | eval case="case(".mvjoin(partial_statement, ",").",true(),risk_score)" 
````

Finally, we are ready to return they dyanmic eval statement however we have to handle the scenario when the case statement is null. Returning a null value would cause the outer eval statement to throw an error because `| eval risk_score= ` is not proper syntax. To do this we use `appendpipe` to count the results, and if the results are 0 set `case` to the string "risk_score". By doing this, the outer eval will run `|eval rule_override=risk_score` which has no affect. This is not a concern for the search macros because `search NOT ()` is technically proper Splunk syntax and just has no effect. Using the above example again, the final eval statement would be `|eval risk_score=case(cidrmatch("10.0.0.1/32",src_cidr) AND like(lower(test),"test.local") AND cidrmatch("192.168.0.0/16",dest_ip),"<risk score value>|<tuning entry id>",true(),risk_score)`

````
    | appendpipe 
        [| stats count 
        | where count=0 
        | eval case="risk_score"] 
    | return $case
````

The last step is to extract `risk_score` and `tuning_entry_id` from the returned `rule_override` field. If the `rule_override` field was set to `risk_score` by the default `case` statement branch or because case statement was null, then this step has no affect on the results, because the regex in `rex` will not match.
````
    | rex field=rule_override "(?<risk_score>\d+)\|(?<tuning_entry_id>.*)"
    | fields - rule_override
````

#### Stress Test
Stress test for risk score macro is done to determine if there is a maximum number of entries or length of string that can be returned before the eval throws an error. To perform a stress test we duplicate the partial_statement multivalue field prior to constructing the case field, then append a single entry for confidence override of our test field. An example of this search is shown below:
````
| makeresults 
| eval test_field="test", risk_score=100
| eval rule_override= 
    [| inputlookup rba_risk_score_override.csv 
    | eval id=sha1(created_time."|".operator."|".field."|".value) 
    | eval field=if(operator="or",split(field,"|"),field) 
    | mvexpand field 
    | eval field=split(field,"|"), value=split(value,"|"), rules=split(rules,"|") 
    | eval first_subnet=mvfind(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$") 
    | eval second_subnet=mvfind(mvindex(value,first_subnet+1,-1),"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$")+first_subnet+1 
    | eval cidr_indexes=mvappend(first_subnet,second_subnet) 
    | eval cidr_fields=mvmap(cidr_indexes,mvindex(field,cidr_indexes))
    | eval tmp_field=field, tmp_value=value 
    | eval combined=if(operator="or",mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),"cidrmatch(\"".value."\",".field.")","like(lower(".field."),\"".value."\")")),mvzip(mvmap(field,if(field in(cidr_fields),"cidrmatch(\"".mvindex(value,tonumber(mvfind(tmp_field,field)))."\"","like(lower(".field.")")),mvmap(value,if(match(value,"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[0-2]?[0-9])$"),",".mvindex(field,tonumber(mvfind(tmp_value,value))).")",",\"".value."\")")),"")), partial_statement=if(operator="or",mvjoin(combined," OR "), mvjoin(combined," AND ")) 
    | eval partial_statement=partial_statement.",\"".coalesce(risk_score,"10")."|".id."\"" 
| stats values(partial_statement) as partial_statement 
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,partial_statement)
| eval partial_statement=mvappend(partial_statement,"test_field=\"test\",500|test_id")
| eval case="case(".mvjoin(partial_statement, ",").",true(),risk_score)"
|return $case]
| rex field=rule_override "(?<risk_score>\d+)\|(?<tuning_entry_id>.*)"
| fields - rule_override
````

The results of our tests are below. The results of these tests our indicative of how risk score override would perform if a single rule had this many entries, not if the entire lookup had this many entries. This type of test does not perform any tests for overall size of lookup and effects on the knowledge bundle. 

| Number of Entries | Length of Search | Time to Evaluate | Result |
|-------------------|------------------|------------------|--------|
| 14913 | 0.9 MB | 1s | Successful |
| 29825 | 1.9 MB | 8s | Successful |
| 59649 | 3.8 MB | 84s | Successful |
| 119297 | 7.5 MB | 355s | Successful |

From these tests, we see that the risk score macro experiences performance degradation much quicker than the suppression macro. This is likely due to the resource utilization of case statment compared to a search statement. Significant performance issues start to occur around 50,000 entries, but the risk score override always worked. This testing proves the solution should be sufficient for our use case.

## Troubleshooting

Below are some common issues we have experienced that cause tuning not to work. 

### Tuning Entry Missing from Lookup

One of the first steps in troubleshooting an issue should be to check whether the entry exists in the tuning lookup. Navigate to the `List/Remove Entry` and search for the missing term. If it exists in the lookup continue to the other common issues, if it does not, work with analysts to get the appropriate values added. Two common causes for the entry to be missing are

* Entry expired and was removed from lookup by saved search
* Entry was never added due to Splunk's warning of potential security risk (Explained in more detail in Dashboard documentation)

### Escaped back slashes in File Paths

Properly escaping backslashes can be tricky due to the multiple stages in the Tuning Framework. To properly an entry which contains back slashes, you must first add 4 backslashes for each single slash in the actual value. For example, to add an entry using the `Add Entry` dashboard which suppresses events when `file_path` equals `C:\Users\Test\Desktop\test_malware.exe`, you would actually need to set field as `file_path` and values as `C:\\\\Users\\\\Test\\\\Desktop\\\\test_malware.exe`. The 4 slashes get escaped and add an entry with two slashes to the lookup `C:\\Users\Test\\Desktop\\test_malware.exe` which will properly escape to a single slash when used with the actual searches.  
  
If there is a problem with tuning for an entry containing backslashes, verify that lookup has 2 slashes for each one slash. This can be done by navigating to the `List/Remove Entry` dashboard and searching for the entry. 

### Tuning Field does not exist in the event

If the entry looks correctly formatted but is still not tuning, verify that all fields used for tuning exist in the final event. This can be done by manually running the Correlation Search or Risk Rule in the Splunk search bar, and confirming the fields exist in the output. Sometimes analysts tune using fields from the raw events. These fields may have been renamed or filtered out of the results in the saved search and therefore wont work. Another common cause is tuning on Asset and Identity enrichment fields. Incident Review performs a secondary enrichment of notables with Asset and Identity framework. This causes some fields like `src_ip` and `dest_ip` to show in the notable drop down but not actually exist as an output from the saved search. 


  



  