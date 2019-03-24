# TSL – Text Scraping Language
Python-based Sublime Text build for processing of a scraping language in pseudo-code

*The TSL Sublime Text package allows you to write and execute pseudo-code style language to process text files with Regular expressions and simple logic. This gives an easy entry to data mining to non-programmers.*

Once installed via Sublime Text's **Package Control**, files with the extension `.tsl` will automatically get **syntax-highlighting** and a **build system**. Force building by choosing **`Tools > Build System > TSL`** from the ST3 menu.

## Example:
![Sublime Text Syntax Highlighting](https://raw.githubusercontent.com/polygoat/TSL/master/preview.png "Sublime Text Syntax Highlighting")

... This will read all lines from `runner/all_utterances.txt`, find all occurences of the string `"dateTime"`, take those lines, remove them and save all lines in `runner/cleaned_utterances`. The removed lines will be stored in `runner/dateTime_utterances.txt` instead, which is cleared out beforehand.

---
# Index
### [How does it work?](#how-does-it-work)
### [Prerequisites](#prerequisites)
### [Available Commands](#available-commands)
### [Templating](#templating)
---
# How does it work?
TSL runs through the script line by line and executes corresponding Python code in the background. File handling, complex data types, and templating are built-in for rapid prototyping. Every line starts with a command followed by a space and space-separated arguments. 
Most commands support optional clauses like `as ...` (storage variable) or `in ...` (file handle) to supply further information.

A command's inputs and outputs can be **strings** or **collections of strings**. In ladder case, TSL iterates over a collection's strings and applies the command to each of them. The commands `as`, `remember`, `split`, and `for every` loops change the context to the provided variable. This means you can omit `as` clauses in the following commands, always automatically referring to the context.

---
# Prerequisites
You need Python >= 3 installed to run TSL scripts.
---
# Available Commands

## File operations

### empty `[<filepath>]`
*Opens up a file and deletes all its content.*

**Example:**
```fortran
    in dateTime_utterances.txt
    	empty
```

### in *`<path/to/textfile.txt>`*
*Opens up a file and reads all its lines. You can log the lines using `log line`
All future file operations are refering to this one until your next "in" statement.
You'll usually see this followed by a `take` or `find all` command*

**Example:**
```fortran
    in myFiles/utterances.txt
```

### in *`<path/to/folder>`*
*Creates the nested directory structure if it doesn't exist. Otherwise, the path will be used as context for future operations.*

**Example:**
```fortran
    in "/Sublime Text/Packages"
        count files as fileCount
        log fileCount
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
*Selects the range from the indicated string/RegEX/number until the indicated string or regular expression or number. Note that we start counting with 1 to keep it natural*

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

---
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

### split *`<string|RegEx>`* by `<delimiter>` as `<variable>`
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

---
## Flow

### for every `<variable>`
### ---

*Loops through a collection, populating the variable `i` with the current index. From within the loop, the item of the collection can be accessed using the same variable name. To access the collection from within the loop use the variable `collection`.*

*Always terminate a loop with three consecutive minus signs in a separte line.*

**Example:**
```fortran
    in utterances.txt
    	find all [^\b]+ as word
    	for every word
    		log "here comes a [word]"
    	---
```
---
# Templating

Templates are enclosed in square brackets and can appear in quoted strings, file paths, and even within regular expressions:
```fortran
{
    remember "\CommNetwork" as domain
    in usernames.txt
        find all \b[domain][^:]: as user
        for every user
            select from 0 to -1
            in /users/[user]/credentials.txt
                change user to "[user]:pleaseresetme"
                add user
        ---
}
```
If the variables can not be found, the template tags remain untouched, including square brackets. This allows us to easily mix them with regular expressions.
