# Add translations to Clean Up!

All language-specific information needed to run the game are stored either as `.template` files or in json format.

1. Copy `./resources/initial_prompts/en` and `./resources/intermittent_prompts/en` and rename using the ISO code of the target language, i.e.:

```
cp ./resources/initial_prompts/en ./resources/initial_prompts/<YOUR_LANGUAGE_CODE>
cp ./resources/intermittent_prompts/en ./resources/intermittent_prompts/<YOUR_LANGUAGE_CODE>
```

2. Go into the folders, and translate each of the templates. Do not change the keywords preceded by `$`

3. Edit the json files. These are: `./resources/commands.json`, `./resources/keywords.json`, `./resources/move_messages.json`, `./resources/parse_errors.json`, `./resources/restricted_literals.json`, `./resources/restricted_patterns.json`. In each file, duplicate the `en` section, rename it with your language code, and translate all values.
     > **IMPORTANT:** Verify that the RegEx patterns actually work as intended for the target language (e.g., use [regex101](https://regex101.com/). For example, `\\b` means word boundary, which is not useful in languages that don't separate words. Look out for numerals that are also used in normal speech, these should not be restricted: e.g. 'Let's move **one** object at a time' should not trigger a penalty.

5. Add your language code to `LANGUAGES` in `instancegenerator.py`
