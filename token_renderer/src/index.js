import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { EuiToken, EuiIcon, EuiProvider } from '@elastic/eui';
import './styles.css';

function App() {
  // Read URL parameters inside the component so they're reactive
  const [params, setParams] = useState(() => {
    const urlParams = new URLSearchParams(window.location.search);
    return {
      iconType: urlParams.get('iconType') || 'tokenSymbol',
      componentType: urlParams.get('componentType'),
      size: urlParams.get('size') || 'm',
    };
  });

  const { iconType, componentType, size } = params;

  // Log what we're rendering for debugging
  useEffect(() => {
    console.log('Rendering:', { iconType, componentType, size, url: window.location.href });
  }, [iconType, componentType, size]);

  // Validate componentType is provided
  if (!componentType || (componentType !== 'icon' && componentType !== 'token')) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        Error: componentType is required and must be "icon" or "token"
        <br />
        Current componentType: {componentType || 'undefined'}
        <br />
        URL: {window.location.href}
      </div>
    );
  }

  return (
    <div className="icon-container">
      <EuiProvider colorMode="light">
        {componentType === 'token' ? (
          <EuiToken iconType={iconType} size={size} />
        ) : (
          <EuiIcon type={iconType} size={size} />
        )}
      </EuiProvider>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

