#!/bin/bash

test_file="test_result_2.txt"

function _StringOrDigital() {
  echo $1 | sed 's/ //g' | sed '/^$/d' | awk '{print($0~/^[-]?([0-9])+[.]?([0-9])+$/)?"number":"string"}'
}

function _IsEqual() {
   echo $1 | awk -v tem=0 '{print($1=tem)? "1":"0"}'
}

function _IsBiggerThan() {
   echo $1 | awk -v tem=0 '{print($1>tem)? "1":"0"}'
}


cols=$(sed '/^$/d' $test_file | awk -F ' : ' '{ print $1 }' | uniq)

max=0.00
for col in ${cols[@]}; do
   # echo "col: $col, max: $max"

   if [ $(_StringOrDigital $col) == "string" ] || [ $col == "0.00" ]; then
      # echo "is string or 0.00, jump"
      continue
   fi

   if [[ $(_StringOrDigital $col) == "number" ]]; then
        if [[ $(_IsBiggerThan $col) -eq "1" ]]; then
	    max=$col
	fi
   fi
done

echo "Max is $max"

# echo "  10.95" | sed 's/ //g' | sed '/^$/d' | awk '{print($0~/^[-]?([0-9])+[.]?([0-9])+$/)?"number":"string"}'
