import '../styles/App.css'

import { testCard } from './text-card'

import { testData } from '../types/data'

function App() {

  return (
    <>
      <header></header>
      <div className="content">
        {testData.map((data) => (testCard(data)))}
      </div>
    </>
  )
}

export default App
