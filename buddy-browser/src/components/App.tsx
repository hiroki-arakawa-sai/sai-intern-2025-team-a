import '../styles/App.css'

import { testCard } from './text-card'
import { RightSide } from './right-side'

import type { Data } from '../types/data'
import { testData } from '../types/data'

import type { Time } from '../types/time'
import { testTimes } from '../types/time'

import { useEffect, useState } from 'react';
function App() {
  const [messages, setMessages] = useState<Data[]>([]);
  const [selectedUser, setSelectedUser] = useState<string>("");
  const [times, setTimes] = useState<Time[]>([]);

  // メッセージと時間取得関数
  const fetchMessages = () => {
    fetch('http://172.16.1.72:8000/api/all') //ボイスメモ取得
      .then((res) => res.json())
      .then((data) => {
        // APIの型をData型に変換
        const converted = data.map((item: { userName: string; message: string; time: string }) => ({
          senderUserName: item.userName,
          text: item.message,
          time: item.time,
          chatBotName: ""
        }));
        setMessages(converted);
      })
      .catch((err) => {
        console.error(err);
        setMessages(testData);
      });
    // Time型配列取得
    fetch('http://0.0.0.0:8000/api/times') //巡回時間取得
      .then((res) => res.json())
      .then((data) => setTimes(data))
      .catch((err) => {
        console.error(err);
        setTimes(testTimes);
      });
  };

  useEffect(() => {
    fetchMessages();
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
        <button onClick={fetchMessages}>更新</button>
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
        <RightSide times={times} setTimes={setTimes} />
      </div>
    </>
  );
}

export default App;
