import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center border border-[#1B3A4B] px-3 text-sm font-medium disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1B3A4B]',
  {
    variants: {
      variant: {
        default: 'bg-[#1B3A4B] text-[#F4F8FA]',
        sticker: 'bg-[#FFE14A] text-[#1B3A4B]',
        quiet: 'bg-transparent text-[#1B3A4B]',
        danger: 'bg-[#E23D3D] text-white border-[#E23D3D]',
      },
      size: {
        default: 'h-10',
        sm: 'h-8',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }

/** 后台按钮。 */
export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
