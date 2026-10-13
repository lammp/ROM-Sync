import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FolderBrowser } from './FolderBrowser'
import * as stories from './FolderBrowser.stories'

const { InAFolder, Drives, AFile } = composeStories(stories)

describe('FolderBrowser', () => {
  it('opens a subfolder and chooses the folder shown', () => {
    render(<InAFolder />)
    fireEvent.click(screen.getByRole('button', { name: 'ROMs' }))
    expect(InAFolder.args.onOpen).toHaveBeenLastCalledWith('D:\\Games\\ROMs')
    fireEvent.click(screen.getByRole('button', { name: 'Choose this folder' }))
    expect(InAFolder.args.onChoose).toHaveBeenCalledWith('D:\\Games')
  })

  it('goes up from a drive root to the drives', () => {
    const onOpen = vi.fn()
    render(
      <FolderBrowser
        title="T"
        kind="folder"
        listing={{ path: 'D:\\', parent: null, folders: [], files: [] }}
        onOpen={onOpen}
        onChoose={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Up' }))
    expect(onOpen).toHaveBeenCalledWith(null)
    expect(screen.getByText('No folders in here.')).toBeTruthy()
  })

  it('offers nothing to choose among the drives', () => {
    render(<Drives />)
    expect(
      (screen.getByRole('button', { name: 'Choose this folder' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('lists files only when choosing a file, and forgets a selection on moving', () => {
    render(<AFile />)
    fireEvent.click(screen.getByRole('button', { name: 'adb.exe' }))
    fireEvent.click(screen.getByRole('button', { name: 'Up' }))
    expect(
      (screen.getByRole('button', { name: 'Choose this file' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('closes on a click outside', () => {
    render(<InAFolder />)
    const around = screen.getByRole('dialog').parentElement
    if (!around) throw new Error('no backdrop')
    fireEvent.mouseDown(around)
    expect(InAFolder.args.onCancel).toHaveBeenCalledOnce()
  })
})
