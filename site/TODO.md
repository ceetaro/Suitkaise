we need to manually check every single module site page and update the docs if needed for the initial release.

circuits - DONE
- why - DONE
- quick start - DONE
- how to use - DONE
- how it works - DONE
- examples - DONE

cucumber
- why - DONE
- quick start - DONE
- how to use - DONE
- how it works
- examples
- supported types - DONE
- performance - DONE
- worst possible object - DONE

timing
- why - DONE
- quick start 
- how to use - DONE
- how it works - DONE
- examples

paths
- why - DONE
- quick start
- how to use - DONE
- how it works - DONE
- examples

processing
- why
- quick start
- how to use
- how it works
- examples

sk
- why - DONE
- quick start
- how to use - DONE
- how it works - DONE
- examples
- blocking calls - DONE


NEXT, we need to:

1. update the about page in the main nav bar
- dropdowns need to be restandardized to the regular style in the module pages
- ensure __about__.md is actually streamlined to look like a site.md file
- copy over to html

2. add the quick start for all modules page on the main nav bar

3. add the feedback page on the main nav bar
- links are in _survey_links.md

4. create the footer for all site pages. make this look professional with the actual social media icons. add the footer to all pages except the password page and loading page.
    - link to each social
        - instagram - https://www.instagram.com/__suitkaise__?igsh=NTc4MTIwNjQ2YQ%3D%3D&utm_source=qr
        - discord - placeholder
        - youtube - placeholder
        - reddit - placeholder
        - twitter - placeholder
        - tiktok - placeholder
        - github - placeholder
        - email - suitkaise@suitkaise.info

    - link to the feedback page in footer as well


5. add the technical info page on the main nav bar


home page showcases

the worst possible object showcase is always what shows up first on the home page. other than that, order is random.

processing 1: at typing speed (about 150 wpm) we showcase a modified version of the 92 vs 40 lines of code example.

1. give the situation: what is getting built?
2. then, we do a side by side. on the left, suitkaise's 40 lines. on the right, 92 lines without it.
3. keep the code on screen so the user can scroll through it.

processing 2: show off Share as the main feature. it is the most "hype" and "out there" feature.

processing 3. show off modified pools with star and sk modifiers.

processing 4. show off a clean skprocess inheriting class that uses @autoreconnect

for cucumber showcase 1: we show a cool monster vs an adventurer. i made the art and put it in assets. this monster is worst possible object. 

1. we show just the monster for a few seconds, somehow showing that that represents the worst possible object.

2. then we change the opacity to about 30-50%. this is where the actual worst possible object code quickly scrolls for about 5 seconds behind the monster image. as it is scrolling, small phrases "pop out" and fall/fade. these are the descriptions of worst possible object in plain language:

- worst possible object pops out first and is slow to fade
- then, "deeply nested"
- "every type"
- randomly generated nested collections
- multiple circular and cross-referenced patterns
- and whatever else we need to get the point across.

make this feel like a boss battle.

then, we need to create the wpo_debug_verbose.py script that serializes and deserializes the worst possible object with debug and verbose enabled. this is so i can get a recording for the site showcase.

we make a blizzard/heavy snowfall effect. as the video plays of worst possible object getting round tripped, this effect plays on top.

then, we show that it did it.

for cucumber showcase 2: we show off the reconnector pattern. lazy reconnect, reconnect all, and auth reconnect.


lets start with these 2 modules.