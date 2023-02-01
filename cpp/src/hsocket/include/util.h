#pragma once
#include <string>
#include <vector>

namespace fileutil {
	bool exists(const char *path);

	bool mkdir(const char *path);

	bool rename(const char *src, const char *dst);

	bool copy(const char *src, const char *dst, bool overwrite = false);

	bool remove(const char *path);

	size_t size(const char *path);

	time_t ctime(const char *path);

	time_t atime(const char *path);

	time_t mtime(const char *path);

	bool exists(const wchar_t *wpath);

	size_t size(const wchar_t *wpath);

	time_t ctime(const wchar_t *wpath);

	time_t atime(const wchar_t *wpath);

	time_t mtime(const wchar_t *wpath);
}

namespace pathutil {
	std::string join(const std::string &path1, const std::string &path2);
}

namespace strutil {
	std::vector<std::string> split(const std::string &s, const std::string &c);

	std::string join(const std::vector<std::string> &v, const std::string &c);
}
