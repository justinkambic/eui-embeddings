import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Prevent FOUC by hiding content until styles load */}
        {/* This ensures Emotion styles are applied before content is visible */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              /* Hide content until styles are loaded to prevent FOUC */
              html { 
                visibility: hidden; 
                opacity: 0; 
              }
              html.loaded { 
                visibility: visible; 
                opacity: 1; 
                transition: opacity 0.05s ease-in;
              }
            `,
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Show content once DOM and styles are ready
              (function() {
                function showContent() {
                  document.documentElement.classList.add('loaded');
                }
                if (document.readyState === 'loading') {
                  document.addEventListener('DOMContentLoaded', showContent);
                } else {
                  // DOM already loaded, but wait a tick for styles
                  setTimeout(showContent, 0);
                }
              })();
            `,
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
