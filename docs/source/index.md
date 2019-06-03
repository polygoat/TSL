# TSL 
## Intuitive **t**ext **s**craping **l**anguage (based&nbsp;on&nbsp;Python)

*TSL is a language in pseudo-code style for processing of text files with Regular Expressions and very basic logic. Behold, **data&nbsp;scientists**, **wranglers**, **scrapers**, and **miners** of the world: no further need for endless Python scripts!*

---
::: splitscreen
* [Key Features](#key-features)
* [Setup](#setup)
* [How it works](#how-it-works)
* [Data](#data)
* [Loops](#loops)

**Available Commands:**
1. [File System Operations](#1-file-system-operations)
2. [Selections](#2-selections)
3. [Debugging & Calculations](#3-debugging-calculations)
4. [Manipulation](#4-manipulation)
5. [Memory](#5-memory)
6. [Flow](#6-flow)
:::
---

## Key Features
### 1. Super-easy file operations with RegEx:
```tsl
{
    # collect all links
    in path/to/posts.csv
        # files ending in csv will automatically be split by semicolon
        split as columns
        find all https?://[\w\.\-0-9]+
        take results as links
        log [columns]
        log [links]
}
```

### 2. Create collections on the fly:
```tsl
{
    split "these are some words" by space as [entities]
    for every [entity]
        # inside the loop we access "entity" as single item of "entities"
        count [entity] as letter-count
    ---
    # and vice versa access a new collection of "letterCount"s after the loop
    log [letter-counts]
}
```

```plain
``output
 letter-counts: [5, 3, 4, 5]
```

### 3. Cherry-pick!

::: splitscreen
```tsl
``Source children.tsl
{
    in /contacts/childnames.tsv
        take lines as children
        log [children]
        for every other [child]
            split [child]
            select 2nd as first-name
        ---
        log " "
        log [first-names]
}
```
```plain
``output
children: [
    "50   Andrea    A",
    "51   Beatrice  B",
    "62   Caroline  C",
    "82   Günther   G"
]

first-names: [
    "Andrea",
    "Caroline"
]
```
:::

---
## Setup
Drop the folder in your Sublime Text's **package directory**. Files with the extension `.tsl` will automatically get **syntax-highlighting** and a **build system** to run them. Force building by choosing **`Tools > Build System > TSL`** from the ST3 menu.

---
## How it works
TSL runs through the script line by line and executes corresponding Python code in the background. File handling, complex data types, and templating are built-in for rapid prototyping. Every line (called **directive**) starts with a command followed by a space and space-separated arguments. 
Most commands support optional **clauses** like `as...` (storage variable) or `in...` (file handle) to supply further context.

```tsl
``Try it out!
{
    log "Hello world!"
}
```
```plain
``output

 Hello world!

```

---
## Data
A command's inputs and outputs can be **strings** or **collections of strings**.

TSL iterates over collections and applies the command to each element. The commands `as`, `remember`, `split`, and `for` change the context to the provided variable. This means you can omit `as` clauses in the following commands, always automatically referring to the context. Use square brackets to reference variables created using e.g. an `as` clause. `log something` will log the string "something", while `log [something]` will log the content of the variable called _something_.

**Templates** (variables) are enclosed in square brackets and can be either passed as reference or appear in _quoted strings_, _file paths_, and even within _regular expressions_:
```tsl
{
    in stats/milestones.tsv
        take lines as rows

        for every [row]
            split by tabs as column
            select second as team-name
            select 3rd as task

            find all [team-name]\:(.*) in [task]
            take results

            in "stats/[team-name].txt"
                write [task]
        ---
}
```
If the variables can not be found, the template tags remain untouched, including square brackets. This allows us to easily mix them with square brackets in regular expressions.

---
## Loops
When working inside `for` loops, TSL automagically uses a **singular version** of your variable to step through the entries of your collection.

```tsl
``extract-names.tsl
{
    in /contacts/childnames.txt
        take lines as children
        log [children]
        for every [child]
            split by tab
            select 2nd as first-name
        ---
    log [first-names]
}
```

Variables created during loops will automatically be appended to a collection named using the plural form. In the example above, the creation of `first-name` **automatically populates** a collection called `first-names`. Irregular plurals like child -> children or foot -> feet have basic support. If the plural fails try compound words for better inflection, e.g. `species-collection` instead of `species`.

---
# Commands
## 1. File & system operations

### **bash** *`<command>`* as *`<variable>`*
#### Runs a bash command and saves the returned output to a variable.

```tsl
    bash git branch as branches
```

### **empty** *`[<filepath>]`*
#### Deletes all content from the last file opened with the `in` command.

```tsl
    in wordbag.txt
        empty
```

### **in** *`<path/to/textfile.txt>`*
#### Opens up a file and reads all its lines. You can log the lines using `log [lines]`. All future file operations are refering to this one until your next "in" statement. You'll usually see this followed by a `take` or `find all` command

```tsl
    in stats/01092019.txt
```

### **in** *`<path/to/folder>`*
#### If it doesn't exist, the (nested) directory structure will be created. The supplied path will be used as context for future operations.

```tsl
    in "/Sublime Text/Packages"
        count files as fileCount
        log [fileCount]
```

### **save** *`[as <filepath>]`*
#### Saves the latest collection in the given filename.

```tsl
    save as runner/cleaned_userinputs.txt
```

### **write** *`[<variable>]`*
#### Writes given variable (or the results of the last `find all`) into the last file opened with `in`

```tsl
    write [userIds]
```

### **add** *`<string/variable>`* *`[to <filepath>]`*
#### Appends content to a file

```tsl
    add [libraries] to libs.txt
```

---

## 2. Selections

### **select** *<n>th* *`[of <input>]`*
#### Selects a specific item of a collection, given its index.

```tsl
    in bigrams.txt   
        select 4th
```


### **select** *words* *`[of <input>]`* *`[as <output>]`*
#### Selects all words found in the last opened file.

```tsl
    in utterances.txt   
        select words
```

### **select** *`[from <string/int/RegEx>]`* *`[to <string/int/RegEx>]`*
#### Selects the range from the indicated string/RegEX/number until the indicated string or regular expression or number. Note that we start counting with 1 to keep it natural.

```tsl
    select from 1 to ";"
    select from \s
    select to \.[a-z]{3}$
    select two of [bigrams]
```

---
## 3. Debugging & calculations

### **be** *`<property>`*
#### Sets one of the following properties of TSL to true:
#### `verbose` or `active`

### **calculate** *`<operation>`* as *`<variable>`*
#### Stores the result of a mathematical calculation and stores it in a variable.

```tsl
    calculate (5 * 4) / 2 as ratio
```

### **log** *`<variable/string>`*
#### Prints to the console. Use strings with template tags (e.g. "here is: [varName]") for variables.

### **count** *`<variable>`* as *`<countVariable>`*
#### Stores the count of items in a collection or characters in a string.

```tsl
    count [entries-per-day] as frequency
    log [frequency]
```

### **count** *`<files/folders>`* *`[in <path/to/dir>]`* as *`<countVariable>`*
#### Stores the count of files or folders in a directory.

```tsl
    count files in "C:\Windows" as system-files
    log "Exactly [system-files] system files found."
```

---
## 4. Manipulation

### **change** *`<varName>`* to *`<formula>`*
#### Iterates over a collection and changes all entries according to the template tag.

```tsl
    change [salute] to "Hi, [salute] #[i]"
```
 *will e.g. change "my name is Dan" to "Hi, my name is Dan #1"*

### **combine** *`<setName>`* with *`<setName>`* as *`<varName>`*
#### Merges two sets and stores it in a new variable.

```tsl
    combine [vowels] with [consonants] as letters
```

### **find** *`<string/RegEx>`* *`[in <varName>]`* *`[as <varName>]`*
#### Finds all occurrences of a string or regular expression in the lines of the currently open file or a stored collection. The results of this search are automatically stored in a variable `found`.

```tsl
    in corpus_de.txt
        take lines as utterances
        find all [aeiou]+ in [utterances]
        log [found]
```

### **remove** lines
#### Removes the last selected lines (e.g. the ones found using a `find all`).

### **replace** *`<string/RegEx>`* by *`<string>`* *`[in <variable>]`*
#### Replaces given string or regular expression by another string, optionally in a particular collection.

```tsl
    replace \W+ by "_"
```

### **sort** `[<varName>]`
#### Sorts either the supplied or last referenced collection alphanumerically (in ascending order).

### **sort** *`[<varName>]`* by *`[<reference>]`*
#### Sorts either the supplied collection by the alphanumerical ascending order of reference collection.

### **split** *`<string/RegEx>`* by *`<delimiter>`* as *`<variable>`*
#### Splits a string into a collection using delimiter. The delimiter can be any combination of characters or one of the following keywords: `brackets`, `commas`, `dots`, `hyphens`, `lines`, `parens`, `periods`, `semicolons`, `spaces`, `tabs`, `underscores`.

```tsl
    split apples;bananas;oranges by semicolons as fruits
    log [fruits]
```

### **unique** *`[<varName>]`*
#### Removes all duplicate entries from given collection.

### **unique** lines
#### Removes all duplicate lines from the last referenced collection.

---
## 5. Memory

### **remember** *`<string/variable>`* as *`<variableName>`*
#### Stores a string or variable in a new variable.

### **take** *`<lines/results/files/folders>`* *`[as <name>]`*
#### Changes the selected collection to whole lines (`take lines as ...`), results of a `find all` directive, or to the files found in a folder specified with a preceding `in <folderPath>` directive.

```tsl
    in source.txt
        find all <[^>]+>
        take lines as htmlLines
        log [htmlLines]
    
    in libraries/de
        take files as germanLibs
        log [germanLibs]
```

---
## 6. Flow

### **for** *`[every]`* *`<variable>`* \newline **---**
#### Loops through a collection, populating the variable `i` with the current index. Use the singular form here to loop through a collection (books -> book, babies -> baby).
#### If a collection is empty, the for-loop is skipped. This is useful to create conditional flows.
#### ! Always terminate a loop with three consecutive hyphens in a separte line.

```tsl
    in corpus.txt
        find all [^\b]+\b[^\b]+ as bigrams
        for every [bigram]
            log "#[i]: [bigram]"
        ---
```

### **run** *`<path/to/script.tsl>`*
#### Runs another TSL file. The external TSL file will receive the same scope as inlined code.