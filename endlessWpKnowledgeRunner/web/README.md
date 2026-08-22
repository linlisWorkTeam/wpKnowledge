# wpKnowledge Dashboard

Start the zero-dependency local dashboard from the runner root:

```powershell
python web/server.py
```

Open <http://127.0.0.1:4174/>.

The dashboard reads the existing `store/` through the local Python runner. It
supports card browsing, search, score signal inspection, liveMode scanning,
explicit `rate`/`correct` feedback, and rescore. It is intended for local
operation, not production exposure.
