# Metrics terminologies 
* `ingredients`: necessary data to compute (sub-)metrics. 
* `sub-metric`: metrics that are used to compute the main metric. 
* `(main) metric`: the bench_score.

`ingredients` and `sub-metrics` should be registered in `ingredients_registry` and `sub_metrics_registry` respectively, in the file `resources/utils/metrics.py`

# Computation flow overview
Running experiments takes a lot of time, but testing the best mapping from `ingredients` to `(sub)metrics` does not. 

We want to separate these two processes. We run experiments to get `ingredients`, with it we can quickly iterate and test different idea of `ingredients -> metrics` mappings. 

> \# business as usual  
> `clem run -g <GAME> -m <MODEL>`  
> `clem transcribe`   
> `clem score`  
> 
> \# testing ideas of mapping   
> make changes to the computation in `MetricCalculator`  
> `python dev_rescore.py`  (hack interactions.json, run `transcribe` and `score` again)

Please note the last step, the script `python dev_rescore.py` updates a small piece of data in `interactions.json`, then call `clem transcribe` to re-generate the transcript, and `clem core` to re-score.   
This is because in `_on_after_game` in `master.py`, the (sub)metrics are also computed and logged to be displayed in `transcript.html` at the end (see `dev:game_finished` in `master.py`), for the reader to get a quick idea of the metrics of an episode.  
If you don't need the (sub)metrics at the end of `transcript.html` to be in sync with the current way of computing metrics, you can replace the last step with `clem score`.   

# Current metrics definition & formulas
All of the ideas below are not final and are open to changes.

## main metric

`main metric` (bench_score) is a harmonic mean of 4 sub-metrics: 

$$bench\_score = harmonic\_mean(distance\_score, consistency\_score, coverage\_score, penalty\_score)$$

$$harmonic\_mean(x_1, .. x_n) = \frac{1}{\sum_{i=1}^{n}\frac{1}{x_i}}$$

Among the sub-metrics, apart from $distance\_score$, we try **not** to give 0 for any other scores. This is because $bench\_score$ is a harmonic mean of all scores.    

The only case that is absolutely bad is when $end\_distance\_sum$ at the end is bigger than randomly scattered objects, in this case we mark it as LOSE (in `_after_game`), and give it 0 as $distance\_score$ as well as  $bench\_score$.

## distance score 

Measures how close the pair-wise identical objects are at the end of the game play.   

$$distance\_score = 1 - mean(\frac{end\_distance\_sum}{expected\_distance\_sum}, \frac{end\_distance\_sum}{initial\_distance\_sum}), $$ 
$$\ \ or\ 0\ when\ end\_distance\_sum > expected\_distance\_sum$$


When $end\_distance\_sum$ > $expected\_distance\_sum$, 
the model performed worse than random, we give it 0 as $distance\_score$, game is LOST, and 0 as $bench\_score$.

## consistency score
Measures how deviated the models are from the most efficient move pattern, indicating how good the model is at describing, differentiating, and targeting at the intended object that it agreed with the other player.

It is computed episode-wise, and at GameMaster level (because both players contribute to it.)
```
Example: 
    player 1: move A (1)
    player 2: move A (2)
    player 1: move B (3) 
    player 2: move B (4)  
From (1) to (2) and from (3) to (4), the players are moving consistently. 
They only shifted the focused object from (2) to (3). 

Conversely, when the moving sequence is like
    player 1: move A
    player 2: move C
    player 1: move B
    player 2: move A
Then between any two consecutive moves, they are always shifting the focus.
```
$$consistency\_score = 1 - \frac{\#focus\_shift - \#min\_focus\_shift}{(\#max\_focus\_shift + 1) - \#min\_focus\_shift}$$  

$$\#min\_focus\_shift = n\_icons - 1$$  
$$\#max\_focus\_shift = max\_rounds * 2$$   
**need more thinking on $\#max\_focus\_shift$..**

## coverage score: 
Measures the percentage of moved objects. It complements $consistency\_score$ (eg. an episode can have $consistency\_score$ 1 because the players didn't move all the objects).

$$coverage\_score = \prod_{i=1}^{n} (\frac{\#moved\_objects + 1}{\#total\_objects + 1})_{player_i}$$

## penalty score

Just the min-max normalization of $\#penalties$, plugged in $y = 1 - x$.

$$penalty\_score = 1 - \frac{\#penalties}{max\_penalties + 1}$$
