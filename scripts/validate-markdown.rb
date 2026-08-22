#!/usr/bin/env ruby
# frozen_string_literal: true

require "pathname"
require "uri"

ROOT = Pathname.new(__dir__).join("..").realpath

def headings(path)
  path.readlines.each_with_object([]) do |line, anchors|
    next unless line.match?(/^[#]{1,6} /)

    anchors << line.sub(/^[#]{1,6} /, "")
                   .strip
                   .downcase
                   .gsub(/[^\p{Alnum}\s-]/, "")
                   .tr(" ", "-")
                   .gsub(/-+/, "-")
  end
end

errors = []
markdown_files = IO.popen(
  ["git", "-C", ROOT.to_s, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "*.md"],
  &:read
).split("\0")

markdown_files.each do |relative|
  source = ROOT.join(relative)
  source.read.scan(/!?\[[^\]]*\]\(([^)]+)\)/).flatten.each do |raw_target|
    target = raw_target.strip.delete_prefix("<").delete_suffix(">")
    next if target.empty? || target.start_with?("#", "http://", "https://", "mailto:")

    path_part, anchor = target.split("#", 2)
    decoded = URI.decode_www_form_component(path_part)
    destination = source.dirname.join(decoded).cleanpath

    unless destination.exist?
      errors << "#{relative}: missing local link target #{target}"
      next
    end

    next if anchor.nil? || anchor.empty? || !destination.file? || destination.extname.downcase != ".md"

    errors << "#{relative}: missing anchor ##{anchor} in #{decoded}" unless headings(destination).include?(anchor.downcase)
  end

  open_mermaid_fence = false
  source.each_line do |line|
    if open_mermaid_fence
      open_mermaid_fence = false if line.strip == "```"
    elsif line.start_with?("```mermaid")
      open_mermaid_fence = true
    end
  end
  errors << "#{relative}: Mermaid fence is not closed" if open_mermaid_fence
end

abort(errors.join("\n")) unless errors.empty?

puts "Markdown links and Mermaid fences passed for #{markdown_files.length} tracked files."
