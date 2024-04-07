# droopescan-guesser
This script tries to guess Drupal plugin versions from droopescan output

# usage
All you have to do is pipe the JSON output from droopescan to the scripts stdin
![](https://github.com/dotPY-hax/droopescan-guesser/blob/main/drupal_guesser.png?raw=true)

```bash
droopescan scan drupal -u http://drupal.inlanefreight.local -o json | python3 guesser.py

```

# how does it work??
The script compares the available files found by droopescan to all tagged releases on git.drupalcode.org - trying to guess the version. It also tells if a guessed release is tagged as "insecure"

# why?
I wanted a script to automate looking up plugin versions - also:

https://github.com/SamJoan/droopescan/issues/73

unfortunately the code style does not fit into the droopescan project thats why I decided to do it like this
