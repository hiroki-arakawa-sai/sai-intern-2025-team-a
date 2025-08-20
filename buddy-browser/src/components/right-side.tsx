import "../styles/right-side.css"

export const RightSide = () => {
  return (
    <div className='right-side side'>
      <form action="">
        <label htmlFor="time-input">時間を入力:</label>
        <input
          type="time"
          id="time-input"
          name="time-input"
        />
      </form>
    </div>
  )
}