// svg-icon-processor.js
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');
const axios = require('axios');

// You'll need to import your EuiIcon component here
// const { EuiIcon } = require('@elastic/eui');

// Replace with your actual API key
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;

if (!ANTHROPIC_API_KEY) {
  console.error('Please set ANTHROPIC_API_KEY environment variable');
  process.exit(1);
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// List of all EuiIcon types - you'll need to populate this with actual icon types
// You can get this from the EuiIcon documentation or source code
const ICON_TYPES = [
  'accessibility',
  'addDataApp',
  'advancedSettingsApp',
  'aggregate',
  'alert',
  'analyze',
  // ... add all your icon types here
  'wrench',
  'zoom'
];

async function renderIconToSVG(iconType) {
  try {
    // Render the React component to static markup
    const iconElement = React.createElement(EuiIcon, { 
      type: iconType,
      size: 'm' // or whatever default size you prefer
    });
    
    const htmlString = renderToStaticMarkup(iconElement);
    
    // Extract just the SVG part if the component wraps it in other elements
    const svgMatch = htmlString.match(/<svg[^>]*>.*<\/svg>/s);
    return svgMatch ? svgMatch[0] : htmlString;
  } catch (error) {
    console.error(`Error rendering icon ${iconType}:`, error.message);
    return null;
  }
}

async function saveSVG(iconType, svgContent) {
  const outputDir = './rendered-icons';
  await fs.mkdir(outputDir, { recursive: true });
  
  const filename = path.join(outputDir, `${iconType}.svg`);
  await fs.writeFile(filename, svgContent, 'utf8');
  return filename;
}

async function askClaude(svgContent, iconType) {
  try {
    const response = await axios.post(
      'https://api.anthropic.com/v1/messages',
      {
        model: 'claude-sonnet-4-20250514',
        max_tokens: 100,
        messages: [
          {
            role: 'user',
            content: `Please describe this SVG icon in 3-7 words for semantic search embeddings, like "person inside circle". The icon type is "${iconType}".\n\n${svgContent}`
          }
        ]
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01'
        }
      }
    );
    
    return response.data.content[0].text.trim();
  } catch (error) {
    if (error.response?.status === 429) {
      console.error('Rate limit hit! Wait before continuing.');
      throw new Error('RATE_LIMIT');
    }
    console.error(`Error calling Claude API:`, error.response?.data || error.message);
    return null;
  }
}

function askUser(question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer.toLowerCase().trim());
    });
  });
}

async function processIcons() {
  const results = [];
  const resultsFile = './icon-descriptions.json';
  
  // Load existing results if file exists
  try {
    const existingResults = await fs.readFile(resultsFile, 'utf8');
    results.push(...JSON.parse(existingResults));
    console.log(`Loaded ${results.length} existing results`);
  } catch (error) {
    console.log('Starting fresh - no existing results file found');
  }
  
  const processedTypes = new Set(results.map(r => r.iconType));
  const remainingTypes = ICON_TYPES.filter(type => !processedTypes.has(type));
  
  console.log(`Processing ${remainingTypes.length} remaining icon types...`);
  
  for (let i = 0; i < remainingTypes.length; i++) {
    const iconType = remainingTypes[i];
    console.log(`\n--- Processing ${iconType} (${i + 1}/${remainingTypes.length}) ---`);
    
    try {
      // Render the icon
      console.log('Rendering SVG...');
      const svgContent = await renderIconToSVG(iconType);
      
      if (!svgContent) {
        console.log(`Skipping ${iconType} - failed to render`);
        continue;
      }
      
      // Save the SVG
      const filename = await saveSVG(iconType, svgContent);
      console.log(`Saved to: ${filename}`);
      
      // Show preview
      console.log('SVG Preview:');
      console.log(svgContent.substring(0, 200) + '...');
      
      // Ask for confirmation
      const proceed = await askUser(`Send "${iconType}" to Claude for description? (y/n/q to quit): `);
      
      if (proceed === 'q' || proceed === 'quit') {
        console.log('Stopping at user request');
        break;
      }
      
      if (proceed !== 'y' && proceed !== 'yes') {
        console.log('Skipping...');
        continue;
      }
      
      // Call Claude API
      console.log('Calling Claude API...');
      const description = await askClaude(svgContent, iconType);
      
      if (description) {
        console.log(`Description: "${description}"`);
        
        const result = {
          iconType,
          description,
          filename,
          processedAt: new Date().toISOString()
        };
        
        results.push(result);
        
        // Save results after each successful call
        await fs.writeFile(resultsFile, JSON.stringify(results, null, 2));
        console.log('Result saved!');
      }
      
      // Small delay to be nice to the API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
    } catch (error) {
      if (error.message === 'RATE_LIMIT') {
        console.log('\nRate limit reached. Results saved. You can resume later by running the script again.');
        break;
      }
      console.error(`Error processing ${iconType}:`, error.message);
    }
  }
  
  rl.close();
  console.log(`\nCompleted! Processed ${results.length} icons total.`);
  console.log(`Results saved to: ${resultsFile}`);
}

// Alternative function if you want to get all icon types programmatically
async function discoverIconTypes() {
  // This would require introspecting your EuiIcon component
  // You might need to check the component's source or documentation
  console.log('You need to manually populate the ICON_TYPES array with all available icon types');
  console.log('Check your EuiIcon component documentation or source code');
}

if (require.main === module) {
  processIcons().catch(console.error);
}