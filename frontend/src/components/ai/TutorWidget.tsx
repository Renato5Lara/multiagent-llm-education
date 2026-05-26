import { useState, useRef, useEffect } from 'react'
import { MessageCircle, X, Send, Bot, User, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useMutation } from '@tanstack/react-query'
import api from '@/lib/api'

interface Message {
  role: 'user' | 'tutor'
  content: string
}

interface TutorWidgetProps {
  courseId: string
  courseName?: string
  moduleTitle?: string
  bloomLevel?: number
}

export default function TutorWidget({
  courseId,
  courseName,
  moduleTitle,
  bloomLevel,
}: TutorWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'tutor',
      content: '¡Hola! Soy tu tutor IA. ¿Tienes alguna duda sobre el curso o los conceptos que estás estudiando?',
    },
  ])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const resp = await api.post('/api/students/tutor/chat', {
        message,
        course_id: courseId,
        context: {
          module_title: moduleTitle,
          bloom_level: bloomLevel,
        },
      })
      return resp.data as { response: string; context?: Record<string, unknown> }
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, { role: 'tutor', content: data.response }])
    },
    onError: () => {
      setMessages(prev => [...prev, {
        role: 'tutor',
        content: 'Lo siento, tuve un problema al procesar tu mensaje. Por favor, intenta de nuevo.',
      }])
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || chatMutation.isPending) return
    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    chatMutation.mutate(userMessage)
  }

  return (
    <>
      <Button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 rounded-full h-14 w-14 shadow-lg hover:shadow-xl transition-all"
        size="icon"
      >
        {isOpen ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </Button>

      {isOpen && (
        <Card className="fixed bottom-24 right-6 z-50 w-80 md:w-96 shadow-2xl border-primary/20">
          <CardContent className="p-0">
            <div className="bg-primary text-primary-foreground p-4 rounded-t-lg flex items-center gap-2">
              <Bot className="h-5 w-5" />
              <div className="flex-1">
                <p className="font-semibold text-sm">Tutor IA</p>
                <p className="text-xs opacity-80">{courseName || 'Asistente educativo'}</p>
              </div>
            </div>

            <div className="h-80 overflow-y-auto p-4 space-y-3 bg-gray-50">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'tutor' && (
                    <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg p-3 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-white border shadow-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </div>
              ))}
              {chatMutation.isPending && (
                <div className="flex gap-2">
                  <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="bg-white border rounded-lg p-3">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-3 border-t bg-white rounded-b-lg">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Escribe tu duda..."
                  className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50"
                  disabled={chatMutation.isPending}
                />
                <Button
                  size="icon"
                  onClick={handleSend}
                  disabled={!input.trim() || chatMutation.isPending}
                  className="flex-shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}
