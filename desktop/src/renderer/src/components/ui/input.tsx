import { cn } from '@/lib/utils'
import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'

/** 单行输入框。 */
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-12 w-full border border-[#1B3A4B] bg-[#F7FBFC] px-3 text-[#243037] outline-none placeholder:text-[#5E7380] focus:bg-white',
        className,
      )}
      {...props}
    />
  )
}

/** 多行输入框。 */
export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'min-h-24 w-full border border-[#1B3A4B] bg-[#F7FBFC] px-3 py-2 text-[#243037] outline-none placeholder:text-[#5E7380] focus:bg-white',
        className,
      )}
      {...props}
    />
  )
}
