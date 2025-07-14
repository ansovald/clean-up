Generated with the following params: 
5 models * 3 languages * 6 experiments * 1 instance/experiment = 90 instances 
daily limit is 1000, 1000 / 90 = 11.11, not enough to cover all instances 

```
LANGUAGES = ['zh-CN', 'en', 'de']  
N_INSTANCES = 1    # for usual overnight testing
ICON_NUM_OPTIONS = [3, 6]

CONFIGS = {
            "2D": {
                "n_nouns": "$$ICON_NUM$$", 
                "colored": True,
                "n_per_color": 1,
            }, 
            "1D": { 
                "n_nouns": 1, 
                "colored": True,
                "n_per_color": "$$ICON_NUM$$",
            }, 
            "0D": {
                "n_nouns": 1,
                "colored": False,
                "n_per_color": "$$ICON_NUM$$",
            }   
        }
```