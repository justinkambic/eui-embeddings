import PageTemplate from "../components/pageTemplate";
import { MainPageContent } from "../components/mainPage/content";
import { useEffect } from "react";

// Performance monitoring for page load
const markPageLoad = () => {
  if (typeof window !== 'undefined' && 'performance' in window) {
    // Mark page load start
    window.performance.mark('home-page-load-start');
    
    // Measure time to interactive
    if ('addEventListener' in window) {
      window.addEventListener('load', () => {
        window.performance.mark('home-page-load-complete');
        try {
          window.performance.measure('home-page-load-time', 'home-page-load-start', 'home-page-load-complete');
          const measure = window.performance.getEntriesByName('home-page-load-time')[0];
          if (measure) {
            console.log(`[Performance] Home page load: ${measure.duration.toFixed(2)}ms`);
          }
        } catch (e) {
          // Ignore if marks don't exist
        }
      });
    }
  }
};

export default function HomePage() {
  useEffect(() => {
    markPageLoad();
    // Mark when component is mounted and rendered
    if (typeof window !== 'undefined' && 'performance' in window && 'mark' in window.performance) {
      window.performance.mark('home-page-rendered');
    }
  }, []);

  return (
    <PageTemplate>
      <MainPageContent />
    </PageTemplate>
  );
}
