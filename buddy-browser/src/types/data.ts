export type Data = {
    chatBotName: string,
    senderUserName: string,
    text: string,
    time: number
}

export const testData: Data[] = [
    {
        chatBotName: "ChatBot",
        senderUserName: "User",
        text: "Hello, world!",
        time: Date.now()
    },
    {
        chatBotName: "ChatBot2",
        senderUserName: "User2",
        text: "Hello, world!!",
        time: Date.now()
    },
    {
        chatBotName: "ChatBot3",
        senderUserName: "User3",
        text: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        time: Date.now()
    },
    {
        chatBotName: "ChatBot3",
        senderUserName: "User3",
        text: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        time: Date.now()
    },
    {
        chatBotName: "ChatBot3",
        senderUserName: "User3",
        text: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        time: Date.now()
    }
];