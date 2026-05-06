import Document, { Html, Head, Main, NextScript, DocumentContext } from 'next/document';
import createEmotionServer from '@emotion/server/create-instance';
import { createEmotionCache } from '../lib/emotionCache';
import React from 'react';

interface DocumentProps {
  emotionStyleTags: React.ReactElement[];
}

export default class MyDocument extends Document<DocumentProps> {
  render() {
    const { emotionStyleTags } = this.props;

    return (
      <Html lang="en">
        <Head>
          {/* Inject Emotion critical CSS before other styles */}
          {emotionStyleTags}
          {/* Prevent FOUC during hydration */}
          <style
            dangerouslySetInnerHTML={{
              __html: `
                /* Hide content until React hydrates to prevent FOUC */
                body { visibility: hidden; }
                body.ready { visibility: visible; }
              `,
            }}
          />
          <script
            dangerouslySetInnerHTML={{
              __html: `
                // Show content once React has hydrated
                (function() {
                  if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                      // Wait for React to hydrate
                      setTimeout(function() {
                        document.body.classList.add('ready');
                      }, 0);
                    });
                  } else {
                    setTimeout(function() {
                      document.body.classList.add('ready');
                    }, 0);
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
}

// `getInitialProps` belongs to `_document` (instead of `_app`),
// it's compatible with static-site generation (SSG).
MyDocument.getInitialProps = async (ctx: DocumentContext) => {
  const originalRenderPage = ctx.renderPage;

  // You can consider sharing the same Emotion cache between all the SSR requests to speed up performance.
  // However, be aware that it can have global side effects.
  const cache = createEmotionCache();
  const { extractCriticalToChunks } = createEmotionServer(cache);

  ctx.renderPage = () =>
    originalRenderPage({
      enhanceApp: (App: any) =>
        function EnhanceApp(props) {
          return <App emotionCache={cache} {...props} />;
        },
    });

  // Call the default Document.getInitialProps to get the rendered HTML
  // This is the key - we call the parent Document's getInitialProps
  const initialProps = await Document.getInitialProps(ctx);
  
  // Extract critical CSS from the rendered HTML
  const emotionStyles = extractCriticalToChunks(initialProps.html);
  const emotionStyleTags = emotionStyles.styles.map((style) => (
    <style
      data-emotion={`${style.key} ${style.ids.join(' ')}`}
      key={style.key}
      dangerouslySetInnerHTML={{ __html: style.css }}
    />
  ));

  return {
    ...initialProps,
    emotionStyleTags,
  };
};
