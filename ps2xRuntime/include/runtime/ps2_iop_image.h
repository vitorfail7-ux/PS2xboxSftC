#pragma once
#include <cstdint>
#include <span>
#include <map>
#include <string>
#include <vector>
#include <utility>

// ROMDIR images whose RESET member is empty and directory begins at offset 0.
// Validate the entire directory before publishing any member bytes.
inline bool parseIopRebootImage(std::span<const uint8_t> data,
                               std::map<std::string, std::vector<uint8_t>> &members)
{
    members.clear();
    if (data.size() < 48 || data.size() > 64u * 1024u * 1024u) return false;
    auto word = [&](size_t p) {
        return uint32_t(data[p]) | uint32_t(data[p+1]) << 8 |
               uint32_t(data[p+2]) << 16 | uint32_t(data[p+3]) << 24;
    };
    if (std::string(reinterpret_cast<const char *>(data.data()), 5) != "RESET" ||
        data[5] != 0 || word(12) != 0 ||
        std::string(reinterpret_cast<const char *>(data.data()+16), 6) != "ROMDIR" || data[22] != 0)
        return false;
    const size_t directorySize = word(28);
    if (directorySize < 48 || directorySize % 16 || directorySize > data.size()) return false;
    std::map<std::string, std::vector<uint8_t>> parsed;
    size_t offset = 0;
    for (size_t pos = 0; pos < directorySize; pos += 16)
    {
        std::string name;
        bool padding = false;
        for (size_t j = 0; j < 10; ++j)
        {
            const uint8_t c = data[pos+j];
            if (!c) { padding = true; continue; }
            if (padding || !((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-')) return false;
            name += static_cast<char>(c);
        }
        if (name.empty()) { members = std::move(parsed); return true; }
        const size_t size = word(pos+12);
        if (offset > data.size() || size > data.size()-offset || parsed.contains(name)) return false;
        parsed.emplace(name, std::vector<uint8_t>(data.begin()+offset, data.begin()+offset+size));
        offset = (offset+size+15u) & ~size_t(15u);
    }
    return false;
}
