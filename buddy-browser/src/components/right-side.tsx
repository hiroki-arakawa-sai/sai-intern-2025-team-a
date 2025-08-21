import "../styles/right-side.css"

import type { Time } from "../types/time"

import { useCallback } from "react";

type RightSideProps = {
  times: Time[];
  setTimes: (t: Time[]) => void;
};

export const RightSide = ({ times, setTimes }: RightSideProps) => {
  // 時間変更時のハンドラ
  const handleTimeChange = useCallback((id: number, newTime: string) => {
    setTimes(times.map(t => t.id === id ? { ...t, time: newTime } : t));
  }, [times, setTimes]);

  // 保存ボタン押下時のPOST処理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch("http://localhost:8000/hook", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(times)
      });
      alert("保存しました");
    } catch (err) {
      alert("保存に失敗しました");
      console.error(err);
    }

    console.log("保存された時間:", times);
  };

  // 追加ボタン押下時の処理
  const handleAdd = () => {
    // 新しいIDを生成（最大ID+1）
    const newId = times.length > 0 ? Math.max(...times.map(t => t.id)) + 1 : 1;
    setTimes([
      ...times,
      { id: newId, time: "00:00", area: "" }
    ]);
  };

  return (
    <div className='right-side side'>
      <form onSubmit={handleSubmit}>
        <label htmlFor="time-input">時間を入力:</label>
        {times.map((time) => (
          <div key={time.id}>
            <input
              type="time"
              id={`time-input-${time.id}`}
              name={`time-input-${time.id}`}
              value={time.time}
              onChange={e => handleTimeChange(time.id, e.target.value)}
            />
            <input
              type="text"
              id={`area-input-${time.id}`}
              name={`area-input-${time.id}`}
              value={time.area}
              onChange={e => setTimes(times.map(t => t.id === time.id ? { ...t, area: e.target.value } : t))}
            />
            <button type="button" onClick={() => setTimes(times.filter(t => t.id !== time.id))}>削除</button>
          </div>
        ))}
        <button type="button" onClick={handleAdd}>追加</button>
        <button type="submit">保存</button>
      </form>
    </div>
  )
}