import "../styles/App.css";

import { RightSide } from "./right-side";
import { testCard } from "./text-card";

import type { Data } from "../types/data";
import { testData } from "../types/data";

import type { Time } from "../types/time";
import { testTimes } from "../types/time";

import { useEffect, useState } from "react";

import buddylog from "../assets/buddylog01.svg";

type TimeRangeBoxProps = {
  year: string;
  month: string;
  date: string;
  start: string;
  end: string;
  setYear: (value: string) => void;
  setMonth: (value: string) => void;
  setDate: (value: string) => void;
  setStart: (value: string) => void;
  setEnd: (value: string) => void;
};

// 時間で絞り込むコンポーネント
export function TimeRangeBox({
  year,
  month,
  date,
  start,
  end,
  setYear,
  setMonth,
  setDate,
  setStart,
  setEnd,
}: TimeRangeBoxProps) {
  return (
    <div className="p-4 flex items-center space-x-2 time-range">
      <label>
        絞り込み
        <br />
      </label>
      <div>
        <input
          type="number"
          value={year}
          onChange={(e) => setYear(e.target.value)}
          placeholder="年"
          className="border rounded p-2 y-100"
        />
        <label>年</label>
        <input
          type="number"
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          placeholder="月"
          className="border rounded p-2 m-12"
        />
        <label>月</label>
        <input
          type="number"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          placeholder="日"
          className="border rounded p-2 d-31"
        />
        <label>
          日<br />
        </label>
        {/* <label>時間: </label> */}
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
    </div>
  );
}

// 親コンポーネント
function App() {
  const [messages, setMessages] = useState<Data[]>([]);
  const [selectedUser, setSelectedUser] = useState<string>("");
  const [times, setTimes] = useState<Time[]>([]);
  
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");
  const [date, setDate] = useState("");
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
    fetch('http://localhost:8000/schedule/entries') //巡回時間取得
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

    // --- 日付と時間フィルター ---
    // timeがnumber型の場合は文字列に変換
    const timeStr = typeof m.time === "number" ? new Date(m.time).toISOString().replace("T", " ").slice(0, 19) : m.time;
    const messageDate = timeStr.slice(0, 10); // "YYYY-MM-DD"
    const [msgYear, msgMonth, msgDay] = messageDate.split("-");
    const messageTime = timeStr.slice(11, 16); // "HH:MM"

    console.log({
      year,
      msgYear,
      month,
      msgMonth,
      date,
      msgDay,
      startTime,
      messageTime,
    });

    if (year !== "" && msgYear !== year.padStart(4, "0")) return false;
    if (month !== "" && msgMonth !== month.padStart(2, "0")) return false;
    if (date !== "" && msgDay !== date.padStart(2, "0")) return false;
    // 時間フィルター
    if (startTime !== "" && messageTime < startTime) return false;
    if (endTime !== "" && messageTime > endTime) return false;

    return true;
  });

  return (
    <>
      <header>
        <img src={buddylog} alt="buffylog" style={{  }} />
        <button onClick={fetchMessages}>更新</button>
      </header>
      <div className="content">
        <div className="side"></div>
        <div className="center-content">
          <div style={{height:"20%", backgroundColor: "#e9fdf7ff"}}>
            <div style={{ display: "flex"}}>
              <h2>メッセージ</h2>
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
            <TimeRangeBox
                year={year}
                month={month}
                date={date}
                start={startTime}
                end={endTime}
                setYear={setYear}
                setMonth={setMonth}
                setDate={setDate}
                setStart={setStartTime}
                setEnd={setEndTime}
              />
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
