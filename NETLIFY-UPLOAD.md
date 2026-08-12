# Deploying the frontend to Netlify

The folder **`netlify-deploy/`** is a complete static site (1.1 MB). Upload it
as-is — no build step, no git integration, no plugins.

## Upload

1. Go to <https://app.netlify.com> and open the **ai-interview-ab** site.
2. Open the **Deploys** tab.
3. Drag the whole **`netlify-deploy`** folder onto the drop zone
   ("Drag and drop your site output folder here").
4. Wait for the deploy to go green, then hard-refresh the site (Ctrl+Shift+R)
   so the browser drops the old cached JS bundle.

Drag the **folder itself**, not its contents, and not a zip.

## Why this deploy matters

The previous build pointed at the Lambda Function URL, which returns 403 to
every unauthenticated request — so every backend call from the live site was
failing. This build points at the API Gateway endpoint instead:

    https://9u9k9ilpvg.execute-api.us-east-1.amazonaws.com

Verified reachable, with correct CORS headers for `ai-interview-ab.netlify.app`.

## Rebuilding it later

    cd frontend
    npm run build
    cd ..
    rm -rf netlify-deploy && cp -r frontend/out netlify-deploy

`frontend/next.config.mjs` sets `output: "export"`, which is what produces
`frontend/out/`.

To point the build at a different backend without editing source:

    NEXT_PUBLIC_API_BASE=https://your-endpoint npm run build

## Note on routes

The site has two pages, exported as `index.html` and `setup.html`. Netlify maps
`/setup` to `setup.html` automatically. Do **not** add a `_redirects` file with
an SPA catch-all (`/* /index.html 200`) — that would break `/setup` by serving
the home page for it.
