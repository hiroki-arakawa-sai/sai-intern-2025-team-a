import '../styles/App.css'

import { testCard } from './text-card'

import type { Data } from '../types/data'
import { testData } from '../types/data'


import { useEffect, useState } from 'react';

function App() {
  const [messages, setMessages] = useState<Data[]>([]);
  const [selectedUser, setSelectedUser] = useState<string>("");

  useEffect(() => {
    fetch('http://localhost:8000/messages')
      .then((res) => res.json())
      .then((data) => setMessages(data))
      .catch((err) => {
        console.error(err);
        setMessages(testData);
      });
  }, []);

  // ユーザー一覧を抽出
  const userList = Array.from(new Set(messages.map(m => m.senderUserName)));

  // 選択されたユーザーのメッセージのみ表示
  const filteredMessages = selectedUser
    ? messages.filter(m => m.senderUserName === selectedUser)
    : messages;

  return (
    <>
      <header>
      </header>
      <div className="content">
        <div className='side'></div>
        <div className="center-content">
          <div style={{display: 'flex', height:'10%'}}>
            <h2>メッセージ</h2>
            <select value={selectedUser} onChange={e => setSelectedUser(e.target.value)}>
              <option value="">全ユーザー</option>
              {userList.map(user => (
                <option key={user} value={user}>{user}</option>
              ))}
            </select>
          </div>
          <div className="message">
            {filteredMessages.map((data) => (testCard(data)))}
          </div>
        </div>
        <div className='side'></div>
      </div>
    </>
  )
}

export default App
