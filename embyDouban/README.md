## embyDouban

Adds to Emby: Douban, Bangumi bgm.tv ratings, links, and tags

- Douban comments: click the userscript icon to see the toggle.
- Douban link: the rating is clickable, or in front of the IMDb link at the bottom.
- Bangumi link: the rating is clickable, or in front of the TMDB link at the bottom.
- Bangumi tag: to the right of the rating. Optional setting: see the script code comments.

![](https://github.com/kjtsune/embyToLocalPlayer/raw/main/embyDouban/embyDouban.jpg)

**FAQ**

* Douban: now searches using the Emby title instead of the imdb id, which reduces accuracy; for reference only, fixes welcome.
* Douban: to use the API reasonably, requests are made only once by default and cached.  
  But occasionally your IP or device may get blacklisted by Douban and return nothing. The symptom is that Douban has the entry and the imdb id is correct, but it's not shown.  
  You can try a different device and IP. Or check again after three days; the browser cache for a failed script is kept for three days.
* bgm.tv: if the match fails, the rating won't show, but the link will. However, the link is usually wrong too.  
  Rating cache strategy: roughly 30 days for older anime and 3 days for new anime.

**Other related scripts**

* [embyToLocalPlayer](https://greasyfork.org/zh-CN/scripts/448648-embytolocalplayer)
  : calls a local player. Requires Python. Supports reporting playback progress.

**Thanks**

- [JayXon/MoreMovieRatings](https://github.com/JayXon/MoreMovieRatings)