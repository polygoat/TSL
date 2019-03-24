# TSL – Text Scraping Language
Python-based CLI for processing of our own text scraping language in pseudo-code

*The TSL Sublime Text package allows you to write and execute pseudo-code style language to process text files with Regular expressions and simple logic. This gives an easy entry to data mining to non-programmers.*

Once installed via Sublime Text's **Package Control**, files with the extension `.tsl` will automatically get **syntax-highlighting** and a **build system**. Force building by choosing **`Tools > Build System > TSL`** from the ST3 menu.

## Example:
```fortran
{
  in runner/all_utterances.txt 
    find all "dateTime"
    take lines as dateTimeLines
    remove lines
    save as runner/cleaned_utterances.txt

  in runner/dateTime_utterances.txt
    empty
    write dateTimeLines
}
```
... This will read all lines from `runner/all_utterances.txt`, find all occurences of the string `"dateTime"`, take those lines, remove them and save all lines in `runner/cleaned_utterances`. The removed lines will be stored in `runner/dateTime_utterances.txt` instead, which is cleared out beforehand.

---

# Available commands

## File operations

### empty `[<filepath>]`

O*pens up a file and deletes all its content.*

**Example:**
```fortran
    in dateTime_utterances.txt
    	empty
```
### in *`<path/to/textfile.txt>`*

*Opens up a file and reads all its lines. You can log the lines using `log line`
All future file operations are refering to this one until your next "in" statement.*

**Example:**
```fortran
    in myFiles/utterances.txt
```
### save `[as <filepath>]`

*Saves the latest collection in the given filename.*

**Example:**
```fortran
    save as [runner/cleaned_utterances.txt]
```
### write `[<variable>]`

*Writes given variable (or the results of the last `find all`) into the last file opened with `in`*

**Example:**
```fortran
    write dateTimeLines
```
### add *`<string | variable>`* [to `<filepath>`]

*Appends content to a file different from the currently open one*

**Example:**
```fortran
    add libraries to libs.txt
```
---

## Selections

### select words

*Selects all words found in the last opened file.*

**Example:**
```fortran
    in utterances.txt	
    	select words
```
### select from *`<string | RegEx | int>`* to *`<string | RegEx | int>`*

*Selects the range from the indicated string/RegEX/number until the indicated string or regular expression or number*

**Example:**
```fortran
    select from "accessibilityApp" to "[v:"
    select from \s to \s
    select from 1 to "[v:samsung.tvSearchAndPlay.Genres:drama]"
```
### select from `<string | RegEx | integer>`

*Selects the range from the indicated string / regular expression / number until the end of the line*

****Example:**
```fortran
    select from "dateTime"
    select from \d\d\d
    select from 122 
```

### select to `<string | RegEx | integer>`

*Selects the range from the beginning of the line to the indicated string / regular expression / number.*

**Example:**
```fortran
    select until "dateTime"
    select until \W
    select until 370  
```
---

## Debugging

### be `<property>`

*Sets one of the following properties of TSL to true:*

`verbose` | `active`

### log *`<variable | string>`*

*Prints to the console. Use strings with template tags (e.g. "here is: [varName]") for variables*

### count `<variable>` as `<countVariable>`

*Stores the count of lines in a selection.*

**Example:**
```fortran
    count libraries as frequency
    log frequency
```
### count *`<files | folders>`* in `<path/to/dir>` as `<countVariable>`

*Stores the count of files or folders in a directory.*

**Example:**
```fortran
    count files in "C:\Windows" as systemFiles
    log "Exactly [systemFiles] system files found."
```
## Manipulation

### change `<varName>` to `<formula>`

*Iterates over a collection and changes all entries according to the template tag. Use brackets to tag variables, like so: `[varName]`*

**Example:**
```fortran
    change utterance to "Hi, [utterance] #[i]"
```
*will e.g. change "my name is Dan" to "Hi, my name is Dan #1"*

### combine `<setName>` with `<setName>` as `<varName>`

*Merges two sets and stores it in a new variable.*

**Example:**
```fortran
    combine vowels with consonants as letters
```
### find all *`<string | RegEx>`* [in `<varName>`]

*Finds all occurrences of a string or regular expression in the lines of the currently open file or a stored collection. The results of this search are automatically stored in a variable `found`*

Example:
```fortran
    in utterances.txt
    	take lines as utterances
    	find all [aeiou]+ in utterances
    	log found
```
### remove lines

*Removes the last selected lines (e.g. the ones found using a `find all`)*

### replace *`<string | RegEx>`* by `<string>` [in `<variable>`]

*Replaces given string or regular expression by another string, optionally in a particular collection.*

**Example:**
```fortran
    replace \W+ by "_"
```
### sort [`<varName>`]

*Sorts either the supplied or last referenced collection alphanumerically (in ascending order).*

### split `<string>` by `<delimiter>` as `<variable>`

Splits a string into a collection using delimiter.

**Example:**
```fortran
    split apples;bananas;oranges by ; as fruits
    log fruits
```
### unique lines

*Removes all duplicate lines from the last referenced collection.*

## Memory

### remember *`<string | variable>`* as `<variableName>`

*Stores a string or variable in a new variable.*

### take *`<lines | results | files | folders>`* [as `<name>`]

*Changes the selected collection to whole lines (`take lines as ...`), results of a `find all` directive, or to the files found in a folder specified with a preceding `in <folderPath>` directive.*

**Example:**
```fortran
    in utterances.txt
    	find all <[^>]+>
    	take lines as htmlLines
    	log htmlLines
    
    in libraries/de
    	take files as germanLibs
    	log germanLibs
```
## Flow

### for every `<variable>`
### ---

*Loops through a collection, populating the variable `i` with the current index. From within the loop, the item of the collection can be accessed using the same variable name. To access the collection from within the loop use the variable `collection`.

Always terminate a loop with three consecutive minus signs in a separte line.*

**Example:**
```fortran
    in utterances.txt
    	find all [^\b]+ as word
    	for every word
    		log "here comes a [word]"
    	---
```
