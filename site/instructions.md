# Instructions

I am making a website layout using pseudo-code in .md files.

I don't know how to make a website, so I am using this so that AI can help me construct it.

Rules:

site is the root dir for the website

each subdir represents a page on the site.

each subdir will have a __file__.md file that is the reference file for that page.

each page can have multiple sections, and those sections can have sub-sections.

the __file__.md file will have the following structure:

/*
a header that gives more info about what i want it to look like.
*/


rows = x
columns = y

note: the row column system is used to determine the layout of sections.

note: use a leading # to reference a section

# x.y = path/to/section

note: all files can contain comments using /*comment*/ syntax.

note: i might also add comments within sections to give more info about what i want it to look like.

note: some files under a dir wont have __file__ pattern. this means that they dont have their own directory or sub-sections.

note: if a background color is defined in a section, and a sub-section doesnt set a background color, then the background color of the section should be used.