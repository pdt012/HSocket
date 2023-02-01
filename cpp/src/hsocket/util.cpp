#include "pch.h"
#include "util.h"
#include <corecrt_io.h>

namespace fileutil {
	bool exists(const char *path)
	{
		return _access(path, 0) == 0;
	}

	bool mkdir(const char *path)
	{
		return CreateDirectoryA(path, NULL);
	}

	bool rename(const char *src, const char *dst)
	{
		return MoveFileA(src, dst);
	}

	bool copy(const char *src, const char *dst, bool overwrite)
	{
		return CopyFileA(src, dst, !overwrite);
	}

	bool remove(const char *path)
	{
		return DeleteFileA(path);
	}

	size_t size(const char *path)
	{
		struct stat st;
		if (::stat(path, &st) == 0)
			return st.st_size;
		else
			return 0;
	}

	time_t ctime(const char *path)
	{
		struct stat st;
		if (::stat(path, &st) == 0)
			return st.st_ctime;
		else
			return 0;
	}

	time_t atime(const char *path)
	{
		struct stat st;
		if (::stat(path, &st) == 0)
			return st.st_atime;
		else
			return 0;
	}

	time_t mtime(const char *path)
	{
		struct stat st;
		if (::stat(path, &st) == 0)
			return st.st_mtime;
		else
			return 0;
	}

	bool exists(const wchar_t *wpath)
	{
		return _waccess(wpath, 0) == 0;
	}

	size_t size(const wchar_t *wpath)
	{
		struct _stat st;
		if (::_wstat(wpath, &st) == 0)
			return st.st_size;
		else
			return 0;
	}

	time_t ctime(const wchar_t *wpath)
	{
		struct _stat st;
		if (::_wstat(wpath, &st) == 0)
			return st.st_ctime;
		else
			return 0;
	}

	time_t atime(const wchar_t *wpath)
	{
		struct _stat st;
		if (::_wstat(wpath, &st) == 0)
			return st.st_atime;
		else
			return 0;
	}

	time_t mtime(const wchar_t *wpath)
	{
		struct _stat st;
		if (::_wstat(wpath, &st) == 0)
			return st.st_mtime;
		else
			return 0;
	}
}

namespace pathutil {
	std::string join(const std::string &path1, const std::string &path2)
	{
		std::string path;
		path.append(path1);
		if (path1[path1.length() - 1] != '/' && path1[path1.length() - 1] != '\\')
			path.append("/");
		int offset2 = (path2[0] == '/' || path2[0] == '\\') ? 1 : 0;
		path.append(path2.substr(offset2, path2.length() - offset2));
		return path;
	}
}

namespace strutil {
	std::vector<std::string> split(const std::string &s, const std::string &c)
	{
		std::vector<std::string> v;
		std::string::size_type pos1, pos2;
		pos2 = s.find(c);
		pos1 = 0;
		while (std::string::npos != pos2)
		{
			v.push_back(s.substr(pos1, pos2 - pos1));

			pos1 = pos2 + c.size();
			pos2 = s.find(c, pos1);
		}
		if (pos1 != s.length())
			v.push_back(s.substr(pos1));
		return v;
	}

	std::string join(const std::vector<std::string> &v, const std::string &c)
	{
		std::string str;
		if (!v.empty())
			str = v[0];
		for (int i = 1; i < v.size(); i++) {
			str += c;
			str += v[i];
		}
		return str;
	}
}
