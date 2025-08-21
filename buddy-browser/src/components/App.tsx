import "../styles/App.css";

import { RightSide } from "./right-side";
import { testCard } from "./text-card";

import type { Data } from "../types/data";

import type { Time } from "../types/time";

import { useEffect, useState } from "react";

type TimeRangeBoxProps = {
  start: string;
  end: string;
  setStart: (value: string) => void;
  setEnd: (value: string) => void;
};

// 時間で絞り込むコンポーネント
export function TimeRangeBox({
  start,
  end,
  setStart,
  setEnd,
}: TimeRangeBoxProps) {
  return (
    <div className="p-4 flex items-center space-x-2">
      <label>時間で絞り込む:</label>
      <input
        type="time"
        value={start}
        onChange={(e) => setStart(e.target.value)}
        className="border rounded p-2"
      />
      <span>から</span>
      <input
        type="time"
        value={end}
        onChange={(e) => setEnd(e.target.value)}
        className="border rounded p-2"
      />
      <span>まで</span>
    </div>
  );
}

// 親コンポーネント
function App() {
  const [messages, setMessages] = useState<Data[]>([]);
  const [selectedUser, setSelectedUser] = useState<string>("");
  const [times, setTimes] = useState<Time[]>([]);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  // メッセージと時間取得関数
  const fetchMessages = () => {
    fetch("http://localhost:8000/api/all") // ボイスメモ取得
      .then((res) => res.json())
      .then((data) => {
        const converted = data.map(
          (item: { userName: string; message: string; time: string }) => {
            console.log("APIから来た time:", item.time); // 👈 確認
            return {
              senderUserName: item.userName,
              text: item.message,
              time: item.time, // ここが "2025-08-21 11:53:33"
              chatBotName: "",
            };
          }
        );
        setMessages(converted);
      })
      .catch((err) => {
        console.error(err);
        setMessages(testData);
      });

    // Time型配列取得
    fetch("http://0.0.0.0:8000/api/times") // 巡回時間取得
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
  const userList = Array.from(new Set(messages.map((m) => m.senderUserName)));

  // ユーザーと時間で絞り込み
  const filteredMessages = messages.filter((m) => {
    // ユーザーフィルター
    if (selectedUser && m.senderUserName !== selectedUser) return false;

    // 時間フィルター
    const messageTime = m.time.slice(11, 16); // "HH:MM" 部分だけ取り出す
    if (startTime && messageTime < startTime) return false;
    if (endTime && messageTime > endTime) return false;

    return true;
  });

  return (
    <>
      <header>
        <button onClick={fetchMessages}>更新</button>
      </header>
      <div className="content">
        <div className="side"></div>
        <div className="center-content">
          <div style={{ display: "flex", height: "10%" }}>
            <h2>メッセージ</h2>

            <TimeRangeBox
              start={startTime}
              end={endTime}
              setStart={setStartTime}
              setEnd={setEndTime}
            />
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
            >
              <option value="">全ユーザー</option>
              {userList.map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </select>
          </div>
          <div className="message">
            {filteredMessages.map((data) => testCard(data))}
          </div>
        </div>
        <RightSide times={times} setTimes={setTimes} />
      </div>
    </>
  );
}

export default App;