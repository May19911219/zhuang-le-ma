import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
import type { ButtonHTMLAttributes } from 'react'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 border border-[#1B3A4B] px-4 text-[15px] font-medium text-[#1B3A4B] transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B3A4B]',
  {
    variants: {
      variant: {
        default: 'bg-[#1B3A4B] text-[#F4F8FA]',
        sticker: 'bg-[#FFE14A] text-[#1B3A4B]',
        quiet: 'bg-transparent',
        danger: 'bg-[#E23D3D] text-white border-[#E23D3D]',
        good: 'bg-[#1F7A45] text-white border-[#1F7A45]',
      },
      size: {
        default: 'h-11',
        sm: 'h-9 px-3 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }

/** 桌面端按钮，样式跟着贴纸配色走。 */
export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
