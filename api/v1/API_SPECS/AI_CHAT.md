### **Create Chat Session**

```
POST /chat-sessions
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  body: {
    title?: string,          // optional, default: "New Chat"
  }
}
Response: {
  status_code: 201,
  body: {
    message: string, 
    success: true,
    data: {
      id: string,        // uuid
      user_id: string,
      title: string,
      created_at: string,     // ISO
      updated_at: string
    }
  }
}
```

### **List Chat Sessions**

```
GET /chat-sessions
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    cursor?: string,
    per_page?: number = 20,
    search?: string,              // search by title
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      details: [
        {
          id: string,
          user_id: string,
          title: string,
          created_at: string
          updated_at: string,
        }
      ],
      pagination: {
        next_cursor: string,
        prev_cursor: string,
        per_page: number,
      }
    }
  }
}
```

### **Update Chat Session**

```
PATCH /chat-sessions/{session_id}/
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  param: { 
    session_id: string 
  },
  body: { 
    title?: string 
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      user_id: string,
      title: string,
      created_at: string,
      updated_at: string
    }
  }
}
```

### **Delete Chat Session**

```
DELETE /chat-sessions/{session_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  param: { 
    session_id: string 
  }
}
Response:
{
  status_code: 204
}
```

### **Send Message**

```
POST /chat-sessions/{session_id}/messages
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  param: { 
    session_id: string 
  },
  body: {
    content: string,
    metadata?: {  // optional
      client_local_id?: string // for optimistic UI mapping
    }
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      session_id: string,
      sender: "user",
      content: string,
      created_at: string,
      updated_at: string
    }
  }
}
```

