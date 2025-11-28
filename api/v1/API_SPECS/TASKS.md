### **Create Task**
```
POST /tasks
Request: {
  header: {
    Authorization: Bearer dhjahsh
  }
  body: {
    name: string,
    description: string,
    due_date: string - ISO Format e.g 2025-11-20T08:00.00Z
  }
},
Response ; {
  status_code: 201
  body: {
    message: string,
    success: boolean, 
    data: {
      name: string,
      description: string,
      due_date: string,
      status: string, - pending
      completed_at: string,
      created_at: string,
      updated_at: string,
    }
  }
}

```

### **List Tasks**
```
GET /tasks
Request: {
  header: {
    Authorization: Bearer dhjahsh
  }
  query: {
    page: number - 1,
    per_page: number - 10,
    status: string - pending,
  }
},
Response: {
  status_code: 200
  body: {
    message: string,
    success: true,
    data: {
      details: [
        {
          name: string,
          description: string,
          due_date: string,
          status: string, - pending
          completed_at: string,
          created_at: string,
          updated_at: string,
        }
      ],
      pagination: {
        page: number,
        per_page: number,
        total_count: number,
        next: number,
        prev: number
      }
    }
  }
}
```

### **Edit Task**
```
PATCH /tasks/{task_id}
Request: {
  header: {
    Authorization: Bearer dhjahsh
  }
  param: {
    task_id: string - uuid
  }
  body: {
    name?: string,
    description?: string,
    due_date?: string - ISO Format e.g 2025-11-20T08:00.00Z
  }
},
Response ; {
  status_code: 200
  body: {
    message: string,
    success: boolean, 
    data: {
      name: string,
      description: string,
      due_date: string,
      status: string, - pending | completed | abandoned
      completed_at: string,
      created_at: string,
      updated_at: string,
    }
  }
}

```
### **Delete Task**
```
DELETE /tasks/{task_id}
Request: {
  header: {
    Authorization: Bearer dhjahsh
  }
  param: {
    task_id: string - uuid
  }
},
Response ; {
  status_code: 204
}
```

### **Toggle Completion**
```
PATCH /tasks/{task_id}/status
Request: {
  header: {
    Authorization: Bearer dhjahsh
  },
  param: {
    task_id: string - uuid
  },
  body: {
    completed: boolean
  }
},
Response ; {
  status_code: 200
  body: {
    message: string,
    success: boolean, 
    data: {
      name: string,
      description: string,
      due_date: string,
      status: string, - completed 
      completed_at: string,
      created_at: string,
      updated_at: string,
    }
  }
}

```