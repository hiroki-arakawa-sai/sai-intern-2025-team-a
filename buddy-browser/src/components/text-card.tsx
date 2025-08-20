import type { Data } from "../types/data";

export const testCard = (data: Data) => {
    return (
        <div className="text-card">
            <p>{data.text}</p>
            <small>{new Date(data.time).toLocaleString()}</small>
        </div>
    );
}