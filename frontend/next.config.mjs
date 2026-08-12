/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a plain static site into `out/` so the build can be uploaded to
  // Netlify by drag-and-drop, with no git integration or build plugin needed.
  // Every route here is client-rendered and talks to the Lambda API directly,
  // so there is no server runtime to give up.
  output: "export",
};

export default nextConfig;
