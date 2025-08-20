import type { Data } from "../types/data";

import "../styles/text-card.css"

export const testCard = (data: Data) => {
    return (
        <div className="text-card">
            <div className="sender">{data.senderUserName}</div>
            <p>{data.text}</p>
            <small>{new Date(data.time).toLocaleString()}</small>
        </div>
    );
}