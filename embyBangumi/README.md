## embyBangumi

Use Bangumi's first-season rating to fill in Emby's Rotten Tomatoes rating (critic rating)

### How it works

Uses the `original title` and `premiere date` that Emby scrapes from TMDB to look up the rating via `api.bgm.tv`.

### Usage

**Configure the ini file, first keep `dry_run = yes` to test the result.**  
**There's no restore feature, back up before use**

1. Download `embyBangumi.zip`
   and extract it to any folder. [Releases page](https://github.com/kjtsune/embyToLocalPlayer/releases/tag/embyBangumi)
2. Fill in `host`, `api_key`, and `user_id` in the `_config.ini` config file according to the comments.
3. Open a terminal in the extracted folder.
4. Install dependencies: `python -m pip install -i http://pypi.douban.com/simple/ --trusted-host=pypi.douban.com/simple requests`
5. Run the command: `python embyBangumi.py`
6. Once it works, set `dry_run = no` and run again.
7. Media library program list > top right: ••• > check "Show": Critic Rating

### Other

* Both the rating and premiere date are based on the first season.
* Movie premiere dates vary greatly between regions, so some searches will fail.  
  If a search returns no results, the premiere date range is extended by 200 days and searched again. Accuracy will decrease.
* If `trust < 0.5` appears in the log, it's because the searched result is incorrect. It will be skipped and not updated.  
  Incorrect results are cached for 7 days; running again after 7 days will retry the search.
* Premiere dates for TV series are usually fine, so the search time range isn't extended for a second search.  
  If `not result` appears in the log, it might be due to NSFW entry restrictions.  
  Or the premiere date in Emby differs from Bangumi's by more than two days.  
  The `not result` state is also kept for 7 days; it will only retry after 7 days.
* Retrying is likely to yield the same result. (Applying for an API key is not being considered for now.)
* Correct results are cached based on how long ago they were released. Released within 90 days: cached for 3 days. Within 1 year: cached for 30 days. Over 1 year: cached for 120 days.
