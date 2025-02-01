import React from 'react';
import KeylogWords from './KeylogWords'; // Import the component
(global as any).random = Math.random;

const App: React.FC = () => {
  return (
    <div className="App">
      <KeylogWords />
    </div>
  );
}

export default App;